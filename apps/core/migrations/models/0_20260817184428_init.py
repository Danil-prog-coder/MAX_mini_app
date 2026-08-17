from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "universities" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(256) NOT NULL UNIQUE,
    "city" VARCHAR(128) NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "budget_places" INT,
    "tuition_price" INT,
    "has_dormitory" BOOL NOT NULL,
    "admission_deadline" DATE
);
COMMENT ON TABLE "universities" IS 'Вуз.';
CREATE TABLE IF NOT EXISTS "users" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "max_user_id" VARCHAR(64) NOT NULL UNIQUE,
    "display_name" VARCHAR(128) NOT NULL,
    "status" VARCHAR(16) NOT NULL,
    "group_name" VARCHAR(128),
    "is_verified_student" BOOL NOT NULL,
    "verification_doc_url" VARCHAR(512),
    "points_balance" INT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "university_id" BIGINT REFERENCES "universities" ("id") ON DELETE SET NULL
);
COMMENT ON COLUMN "users"."status" IS 'school: school\napplicant: applicant\nstudent: student';
COMMENT ON TABLE "users" IS 'Профиль пользователя — единственный источник правды о нём (ТЗ 1.3, 3).';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "Ne+ZInHPR2+1bx8Q+z+38BFMVsGg=="
)
