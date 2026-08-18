from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "admission_programs" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "passing_score" INT NOT NULL,
    "budget_places" INT NOT NULL,
    "direction_id" BIGINT NOT NULL REFERENCES "directions" ("id") ON DELETE CASCADE,
    "university_id" BIGINT NOT NULL REFERENCES "universities" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_admission_p_univers_82b0da" UNIQUE ("university_id", "direction_id")
);
COMMENT ON TABLE "admission_programs" IS 'Направление в конкретном вузе: то, куда подают документы (тех. ТЗ 3.3).';
        CREATE TABLE IF NOT EXISTS "exam_scores" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "subject" VARCHAR(64) NOT NULL,
    "score" INT NOT NULL,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_exam_scores_user_id_f9bfa8" UNIQUE ("user_id", "subject")
);
COMMENT ON TABLE "exam_scores" IS 'Балл ЕГЭ по одному предмету (тех. ТЗ 3.3).';
        CREATE TABLE IF NOT EXISTS "tracked_vuzy" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "added_at" TIMESTAMPTZ NOT NULL,
    "direction_id" BIGINT REFERENCES "directions" ("id") ON DELETE SET NULL,
    "university_id" BIGINT NOT NULL REFERENCES "universities" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_tracked_vuz_user_id_c6563d" UNIQUE ("user_id", "university_id")
);
COMMENT ON TABLE "tracked_vuzy" IS 'Вуз, добавленный в отслеживаемые из карточки (ТЗ 2.7, тех. ТЗ 3.3).';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "admission_programs";
        DROP TABLE IF EXISTS "exam_scores";
        DROP TABLE IF EXISTS "tracked_vuzy";"""


MODELS_STATE = (
    "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"
    "1/8DJ/rMXw=="
)
