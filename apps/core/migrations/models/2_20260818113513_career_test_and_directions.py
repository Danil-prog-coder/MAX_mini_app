from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "directions" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "code" VARCHAR(64) NOT NULL UNIQUE,
    "name" VARCHAR(128) NOT NULL UNIQUE,
    "summary" VARCHAR(512) NOT NULL,
    "profile_weights" JSONB NOT NULL,
    "required_subjects" JSONB NOT NULL,
    "vacancy_queries" JSONB NOT NULL
);
COMMENT ON TABLE "directions" IS 'Направление подготовки.';
        CREATE TABLE IF NOT EXISTS "career_test_questions" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "order" INT NOT NULL UNIQUE,
    "text" VARCHAR(512) NOT NULL
);
COMMENT ON TABLE "career_test_questions" IS 'Вопрос теста.';
        CREATE TABLE IF NOT EXISTS "career_test_options" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "order" INT NOT NULL,
    "text" VARCHAR(256) NOT NULL,
    "weight_vector" JSONB NOT NULL,
    "question_id" BIGINT NOT NULL REFERENCES "career_test_questions" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_career_test_questio_df26e8" UNIQUE ("question_id", "order")
);
COMMENT ON TABLE "career_test_options" IS 'Вариант ответа.';
        CREATE TABLE IF NOT EXISTS "career_test_results" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "profile" JSONB NOT NULL,
    "top_directions" JSONB NOT NULL,
    "ai_explanation" TEXT NOT NULL,
    "saved_to_profile" BOOL NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "career_test_results" IS 'Результат прохождения.';
        CREATE TABLE IF NOT EXISTS "points_transactions" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "amount" INT NOT NULL,
    "reason" VARCHAR(32) NOT NULL,
    "subject" VARCHAR(64) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_points_tran_user_id_c1508f" UNIQUE ("user_id", "reason", "subject")
);
COMMENT ON COLUMN "points_transactions"."reason" IS 'career_test: career_test\ndaily_checkin: daily_checkin\nmentor_answer: mentor_answer\nreward: reward';
COMMENT ON TABLE "points_transactions" IS 'Одно начисление или списание.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "career_test_results";
        DROP TABLE IF EXISTS "directions";
        DROP TABLE IF EXISTS "career_test_options";
        DROP TABLE IF EXISTS "career_test_questions";
        DROP TABLE IF EXISTS "points_transactions";"""


MODELS_STATE = (
    "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"
)
