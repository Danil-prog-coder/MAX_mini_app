from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "personal_deadlines" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(256) NOT NULL,
    "due_date" DATE NOT NULL,
    "notified" BOOL NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "personal_deadlines" IS 'Личный дедлайн пользователя (ТЗ 4.5, 4.6).';
        CREATE TABLE IF NOT EXISTS "study_groups" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "university_id" BIGINT NOT NULL REFERENCES "universities" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_study_group_univers_549fd3" UNIQUE ("university_id", "name")
);
COMMENT ON TABLE "study_groups" IS 'Учебная группа вуза.';
        CREATE TABLE IF NOT EXISTS "lessons" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "weekday" INT NOT NULL,
    "starts_at_minutes" INT NOT NULL,
    "ends_at_minutes" INT NOT NULL,
    "title" VARCHAR(128) NOT NULL,
    "room" VARCHAR(32) NOT NULL,
    "kind" VARCHAR(32) NOT NULL,
    "group_id" BIGINT NOT NULL REFERENCES "study_groups" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_lessons_group_i_4af36c" UNIQUE ("group_id", "weekday", "starts_at_minutes")
);
COMMENT ON TABLE "lessons" IS 'Пара в недельном расписании группы.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "study_groups";
        DROP TABLE IF EXISTS "personal_deadlines";
        DROP TABLE IF EXISTS "lessons";"""


MODELS_STATE = (
    "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"
    "tQ=="
)
