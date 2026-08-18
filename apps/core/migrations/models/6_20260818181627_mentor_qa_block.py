from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "questions" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "topic" VARCHAR(16) NOT NULL,
    "text" TEXT NOT NULL,
    "moderation_status" VARCHAR(16) NOT NULL,
    "moderation_reason" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "author_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "university_id" BIGINT NOT NULL REFERENCES "universities" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "questions"."topic" IS 'admission: admission\nstudy: study\nstudent_life: student_life';
COMMENT ON COLUMN "questions"."moderation_status" IS 'pending: pending\npublished: published\nrejected: rejected\nmanual_review: manual_review';
COMMENT ON TABLE "questions" IS 'Вопрос в ленте вуза (ТЗ 5.4, 5.5).';
        CREATE TABLE IF NOT EXISTS "answers" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "text" TEXT NOT NULL,
    "likes_count" INT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "author_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "question_id" BIGINT NOT NULL REFERENCES "questions" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "answers" IS 'Ответ верифицированного студента этого вуза (ТЗ 5.6, уточнение У17).';
        CREATE TABLE IF NOT EXISTS "answer_likes" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL,
    "answer_id" BIGINT NOT NULL REFERENCES "answers" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_answer_like_answer__11bad7" UNIQUE ("answer_id", "user_id")
);
COMMENT ON TABLE "answer_likes" IS 'Лайк ответа (ТЗ 5.8).';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "questions";
        DROP TABLE IF EXISTS "answers";
        DROP TABLE IF EXISTS "answer_likes";"""


MODELS_STATE = (
    "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"
)
