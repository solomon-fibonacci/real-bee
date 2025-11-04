"""
Database manager for PostgreSQL operations
"""
import asyncio
from typing import Any, Dict, List, Optional, Type
from contextlib import asynccontextmanager
import asyncpg
from pydantic import BaseModel

from .core import FrameworkConfig
from .exceptions import DatabaseException
from .utils import get_table_name, serialize_for_json


class DatabaseManager:
    """Manages PostgreSQL connections and operations"""

    def __init__(self, config: FrameworkConfig):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.config.postgres_url,
                min_size=1,
                max_size=self.config.postgres_pool_size,
                max_inactive_connection_lifetime=300,
            )
        except Exception as e:
            raise DatabaseException(f"Failed to initialize database pool: {e}")

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection from pool"""
        if not self.pool:
            raise DatabaseException("Database pool not initialized")

        async with self.pool.acquire() as connection:
            yield connection

    async def create_table(self, entity_type: Type[BaseModel]):
        """Create table for entity type"""
        table_name = get_table_name(entity_type)

        # Build column definitions from Pydantic model
        columns = []
        columns.append("id SERIAL PRIMARY KEY")

        for field_name, field in entity_type.model_fields.items():
            if field_name == "id":
                continue

            # Map Python types to PostgreSQL types
            pg_type = self._get_pg_type(field.annotation)
            nullable = "NULL" if self._is_optional(field.annotation) else "NOT NULL"
            columns.append(f"{field_name} {pg_type} {nullable}")

        # Add timestamps
        columns.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        columns.append("updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        columns_sql = ", ".join(columns)

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {columns_sql}
        )
        """

        async with self.acquire() as conn:
            await conn.execute(create_table_sql)

            # Create update trigger for updated_at
            trigger_sql = f"""
            CREATE OR REPLACE FUNCTION update_{table_name}_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';

            DROP TRIGGER IF EXISTS update_{table_name}_updated_at_trigger ON {table_name};

            CREATE TRIGGER update_{table_name}_updated_at_trigger
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION update_{table_name}_updated_at();
            """
            await conn.execute(trigger_sql)

    def _get_pg_type(self, python_type: Any) -> str:
        """Map Python type to PostgreSQL type"""
        # Handle Optional types
        if hasattr(python_type, "__origin__"):
            args = getattr(python_type, "__args__", ())
            python_type = next((arg for arg in args if arg is not type(None)), python_type)

        type_map = {
            int: "INTEGER",
            float: "DOUBLE PRECISION",
            str: "TEXT",
            bool: "BOOLEAN",
            dict: "JSONB",
            list: "JSONB",
        }

        return type_map.get(python_type, "TEXT")

    def _is_optional(self, field_type: Any) -> bool:
        """Check if field type is Optional"""
        if hasattr(field_type, "__origin__"):
            args = getattr(field_type, "__args__", ())
            return type(None) in args
        return False

    async def create(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record"""
        # Remove None values and id
        data = {k: v for k, v in data.items() if v is not None and k != 'id'}

        if not data:
            raise DatabaseException("No data to insert")

        columns = list(data.keys())
        placeholders = [f"${i + 1}" for i in range(len(columns))]
        values = [serialize_for_json(data[col]) for col in columns]

        query = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        RETURNING *
        """

        async with self.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row)

    async def get(self, table_name: str, entity_id: int) -> Optional[Dict[str, Any]]:
        """Get a record by ID"""
        query = f"SELECT * FROM {table_name} WHERE id = $1"

        async with self.acquire() as conn:
            row = await conn.fetchrow(query, entity_id)
            return dict(row) if row else None

    async def list(
        self,
        table_name: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List records with pagination"""
        query = f"SELECT * FROM {table_name}"
        params = []

        if filters:
            where_clauses = []
            param_count = 1
            for key, value in filters.items():
                where_clauses.append(f"{key} = ${param_count}")
                params.append(serialize_for_json(value))
                param_count += 1

            query += " WHERE " + " AND ".join(where_clauses)

        query += f" ORDER BY id DESC OFFSET ${len(params) + 1} LIMIT ${len(params) + 2}"
        params.extend([skip, limit])

        async with self.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def update(
        self,
        table_name: str,
        entity_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a record"""
        # Remove None values and id
        updates = {k: v for k, v in updates.items() if k != 'id'}

        if not updates:
            return await self.get(table_name, entity_id)

        set_clauses = []
        values = []
        param_count = 1

        for key, value in updates.items():
            set_clauses.append(f"{key} = ${param_count}")
            values.append(serialize_for_json(value))
            param_count += 1

        values.append(entity_id)

        query = f"""
        UPDATE {table_name}
        SET {', '.join(set_clauses)}
        WHERE id = ${param_count}
        RETURNING *
        """

        async with self.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None

    async def delete(self, table_name: str, entity_id: int) -> bool:
        """Delete a record"""
        query = f"DELETE FROM {table_name} WHERE id = $1 RETURNING id"

        async with self.acquire() as conn:
            row = await conn.fetchrow(query, entity_id)
            return row is not None

    async def bulk_create(
        self,
        table_name: str,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Bulk insert records"""
        if not items:
            return []

        results = []
        async with self.acquire() as conn:
            async with conn.transaction():
                for item in items:
                    try:
                        result = await self.create(table_name, item)
                        results.append(result)
                    except Exception as e:
                        # Log error but continue with other items
                        print(f"Error creating item: {e}")

        return results

    async def count(self, table_name: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        params = []

        if filters:
            where_clauses = []
            param_count = 1
            for key, value in filters.items():
                where_clauses.append(f"{key} = ${param_count}")
                params.append(serialize_for_json(value))
                param_count += 1

            query += " WHERE " + " AND ".join(where_clauses)

        async with self.acquire() as conn:
            return await conn.fetchval(query, *params)
