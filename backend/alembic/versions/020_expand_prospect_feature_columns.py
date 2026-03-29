"""Expand prospect lab feature columns for raw and advanced college stats."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "020_expand_prospect_feature_columns"
down_revision = "019_trust_infrastructure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in [
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_games INTEGER",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_targets DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_receptions DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_receiving_yards DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_receiving_tds DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_routes_run DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_carries DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_rushing_yards DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_rushing_tds DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_pass_attempts DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_completions DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_passing_yards DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_passing_tds DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_interceptions DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_yprr DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_ypt DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_ypc DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_ypa DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_pass_td_rate DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_qb_rush_yards DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_qb_rush_tds DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_qb_rush_ypg DOUBLE",
        "ALTER TABLE historical_prospect_features ADD COLUMN IF NOT EXISTS college_scramble_rate DOUBLE",
    ]:
        op.execute(statement)


def downgrade() -> None:
    # DuckDB does not consistently support dropping many columns in-place across versions.
    pass
