from pyspark.sql import SparkSession

from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import FixedType, NestedField, UUIDType

import os

# run with `python tests/pyspark_test.py`

# Set environment variables
os.environ["AWS_ACCESS_KEY_ID"] = "admin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "password"
os.environ["AWS_REGION"] = "us-east-1"

# Create a Spark session with Iceberg configurations
# https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.5.2/
iceberg_jar_path = "tests/iceberg-spark-runtime-3.5_2.12-1.5.2.jar"
# https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.5.0/
aws_sdk_s3_jar_path = "tests/iceberg-aws-bundle-1.5.0.jar"
spark = (
    SparkSession.builder.appName("IcebergExample")
    .config("spark.jars", f"{iceberg_jar_path},{aws_sdk_s3_jar_path}")
    .config(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    )
    .config("spark.sql.catalog.rest", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.rest.type", "rest")
    .config("spark.sql.catalog.rest.uri", "http://localhost:8000")
    .config("spark.sql.catalog.rest.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.rest.warehouse", "s3://warehouse/rest/")
    .config("spark.sql.catalog.rest.s3.endpoint", "http://127.0.0.1:9000")
    .config("spark.sql.defaultCatalog", "rest")
    .config("spark.sql.catalogImplementation", "in-memory")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

# .config("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkSessionCatalog") \
# .config("spark.sql.catalog.spark_catalog.type", "hadoop") \
# .config("spark.sql.catalog.spark_catalog.warehouse", "path_to_your_warehouse_directory") \
# .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
# .config("spark.eventLog.enabled", "true") \
# .config("spark.eventLog.dir", "/home/iceberg/spark-events") \
# .config("spark.history.fs.logDirectory", "/home/iceberg/spark-events") \


catalog = load_catalog(
    "rest",
    **{
        "type": "rest",
        "uri": "http://localhost:8000",
        "warehouse": "s3://warehouse/rest/",
        "s3.endpoint": "http://127.0.0.1:9000",
        "s3.access-key-id": "admin",
        "s3.secret-access-key": "password",
    },
)

catalog_name = "rest"

# create a namespace with spark sql
spark.sql(
    f"""
    CREATE DATABASE IF NOT EXISTS {catalog_name}.default;
"""
)

# create a table with pyiceberg
schema = Schema(
    NestedField(field_id=1, name="uuid_col", field_type=UUIDType(), required=False),
    NestedField(field_id=2, name="fixed_col", field_type=FixedType(25), required=False),
)

catalog.create_table(
    identifier="default.test_uuid_and_fixed_unpartitioned", schema=schema
)

# write to table with spark sql
spark.sql(
    f"""
    INSERT INTO {catalog_name}.default.test_uuid_and_fixed_unpartitioned VALUES
    ('102cb62f-e6f8-4eb0-9973-d9b012ff0967', CAST('1234567890123456789012345' AS BINARY)),
    ('ec33e4b2-a834-4cc3-8c4a-a1d3bfc2f226', CAST('1231231231231231231231231' AS BINARY)),
    ('639cccce-c9d2-494a-a78c-278ab234f024', CAST('12345678901234567ass12345' AS BINARY)),
    ('c1b0d8e0-0b0e-4b1e-9b0a-0e0b0d0c0a0b', CAST('asdasasdads12312312312111' AS BINARY)),
    ('923dae77-83d6-47cd-b4b0-d383e64ee57e', CAST('qweeqwwqq1231231231231111' AS BINARY));
    """
)

tbl = catalog.load_table("default.test_uuid_and_fixed_unpartitioned")
assert tbl.schema() == schema
df = tbl.scan().to_arrow().to_pandas()
assert len(df) == 5
assert b"1234567890123456789012345" in df["fixed_col"].to_list()

# create a table with spark sql
spark.sql(
    f"""
    CREATE OR REPLACE TABLE {catalog_name}.default.test_null_nan
    USING iceberg
    AS SELECT
    1            AS idx,
    float('NaN') AS col_numeric
UNION ALL SELECT
    2            AS idx,
    null         AS col_numeric
UNION ALL SELECT
    3            AS idx,
    1            AS col_numeric
"""
)
