from backend.app.models.user import User


def test_user_model_has_columns():
    column_names = [column.name for column in User.__table__.columns]
    expected = {"id", "email", "full_name", "hashed_password", "is_active", "created_at", "updated_at"}
    assert expected.issubset(set(column_names))


def test_user_model_primary_key():
    pk_columns = [column.name for column in User.__table__.primary_key.columns]
    assert "id" in pk_columns


def test_user_model_email_field_exists():
    email_column = User.__table__.columns.get("email")
    assert email_column is not None
