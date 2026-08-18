from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    # Правка сгенерированного aerich текста: NOT NULL добавляется через
    # DEFAULT '' со снятием умолчания следующей строкой. Без этого миграция
    # падает на таблице, в которой уже есть вузы, — а пустые значения тут же
    # перетрёт ближайшая заливка справочника (`python -m navigator.seed`).
    return """
        ALTER TABLE "universities" ADD "address" VARCHAR(256) NOT NULL DEFAULT '';
        ALTER TABLE "universities" ALTER COLUMN "address" DROP DEFAULT;
        ALTER TABLE "universities" ADD "short_name" VARCHAR(64) NOT NULL DEFAULT '';
        ALTER TABLE "universities" ALTER COLUMN "short_name" DROP DEFAULT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "universities" DROP COLUMN "address";
        ALTER TABLE "universities" DROP COLUMN "short_name";"""


MODELS_STATE = (
    "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"
    "9/8Cjy/0ew=="
)
