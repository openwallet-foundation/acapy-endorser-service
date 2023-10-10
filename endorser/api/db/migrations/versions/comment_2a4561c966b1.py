"""comment

Revision ID: 2a4561c966b1
Revises: 88a8b238970b
Create Date: 2023-09-27 23:20:49.343565

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '2a4561c966b1'
down_revision = '88a8b238970b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('endorserequest', sa.Column('ledger_txn_request', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('endorserequest', 'ledger_txn_request')
    # ### end Alembic commands ###