"""add trigram index on products.title

Revision ID: c4e8a1f07b2d
Revises: 1db689a02a76
Create Date: 2026-11-11 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4e8a1f07b2d'
down_revision: Union[str, Sequence[str], None] = '1db689a02a76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Расширение не создаётся autogenerate, поэтому миграция написана вручную
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_products_title_trgm",
        "products",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_products_title_trgm", table_name="products")
    # Расширение намеренно не удаляем: им могут пользоваться другие объекты