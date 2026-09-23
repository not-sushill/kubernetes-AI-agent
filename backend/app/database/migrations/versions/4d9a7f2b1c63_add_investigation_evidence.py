from alembic import op
import sqlalchemy as sa


revision = "4d9a7f2b1c63"
down_revision = "0e75593ba950"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("investigations")
    }

    if "evidence" not in columns:
        with op.batch_alter_table("investigations") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "evidence",
                    sa.Text(),
                    nullable=False,
                    server_default="{}",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("investigations")
    }

    if "evidence" in columns:
        with op.batch_alter_table("investigations") as batch_op:
            batch_op.drop_column("evidence")