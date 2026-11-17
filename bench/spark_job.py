"""Platform-level KPI aggregation with PySpark (local[*] mode).

python bench/spark_job.py --input data/ads_100k.csv|.parquet
"""
import argparse
import os
import sys
import time

from _common import BASE, emit


def ensure_java() -> None:
    if not os.environ.get("JAVA_HOME"):
        for cand in (os.path.join(sys.prefix, "lib", "jvm"), sys.prefix):
            if os.path.exists(os.path.join(cand, "bin", "java")):
                os.environ["JAVA_HOME"] = cand
                break


def session():
    ensure_java()
    from pyspark.sql import SparkSession
    s = (SparkSession.builder.master("local[*]").appName("budget-pilot-bench")
         .config("spark.ui.enabled", "false").config("spark.driver.memory", "3g")
         .config("spark.sql.shuffle.partitions", "8").getOrCreate())
    s.sparkContext.setLogLevel("ERROR")
    return s


def run(spark, path: str) -> dict:
    from pyspark.sql import functions as F
    from pyspark.sql.types import (DoubleType, LongType, StringType, StructField, StructType)
    if path.endswith(".parquet"):
        df = spark.read.parquet(path)
    else:
        schema = StructType([StructField("date", StringType()), StructField("campaign", StringType()),
                             StructField("platform", StringType()), StructField("impressions", LongType()),
                             StructField("clicks", LongType()), StructField("spend", DoubleType()),
                             StructField("conversions", LongType()), StructField("revenue", DoubleType()),
                             StructField("age", StringType()), StructField("gender", StringType()),
                             StructField("city", StringType()), StructField("device", StringType())])
        df = spark.read.csv(path, header=True, schema=schema)
    rows = df.groupBy("platform").agg(*[F.sum(c).alias(c) for c in BASE]).collect()
    return {r["platform"]: [float(r[c]) for c in BASE] for r in rows}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    a = ap.parse_args()
    t_s = time.perf_counter()
    spark = session()
    startup = time.perf_counter() - t_s
    t0 = time.perf_counter()
    sums = run(spark, os.path.abspath(a.input))
    compute = time.perf_counter() - t0
    spark.stop()
    emit("spark", a.input, sums, startup, compute)
