# Databricks notebook source
# MAGIC md
# COMMAND ---------- DBTITLE 1, MVP Gap Suspecting -------------------->
dbutils.widgets.dropdown("env", ["DEV", "QA", "STG", "PROD"])
dbutils.widgets.text("plan_name", "")
env = dbutils.widgets.get("env").lower()
plan_name = dbutils.widgets.get("plan_name").lower()
env_bucket = "pop-" + env
ma_reference = "ma_reference"

# COMMAND ---------- DBTITLE 1, Configuration Setup
from src.spark_helpers.databricks_util import get_plan_name, get_schema_plan_name
plan_name = get_plan_name(plan_name)
schema_plan_name = get_schema_plan_name(plan_name)

schema = plan_name + "transformation"
schema_cur = plan_name + "curation"
schema_ing = plan_name + "ingestion"
schema_gap = plan_name + "gap_curation"

# MAGIC md
# COMMAND ---------- DBTITLE 1, Method Metadata
from pyspark.sql.functions import col

df_method_metadata = spark.table(f"{catalog}.{ma_reference}.ref_method_metadata1").alias("method_meta")

# Both EXCLUSION_TYPE is NA -> inclusion list
df_method_metadata_inclusion = (
    df_method_metadata
        .filter(
            ((col("METHOD_ID")==1) | (col("METHOD_ID")==2) | (col("METHOD_ID")==10)) &
            (col("PROGRAM")=="CMS") &
            (col("EXCLUSION_TYPE_1")=="NA") &
            (col("EXCLUSION_TYPE_2")=="NA")
        )
        .select("*")
)

print(df_method_metadata_inclusion.count())
# COMMAND ---------- DBTITLE 1, Display -- Method Metadata for 1,2,10 (Inclusions only)
display(df_method_metadata_inclusion)

# MAGIC md
# COMMAND ---------- Step 2: Method metadata analysis against CMS ICD-HCC mapping
df_hcc_main = spark.table(f"{catalog}.{ma_reference}.icd_hcc_mapping").alias("icd_hcc")
print("HCC Count: ", df_hcc_main.count())

df_method_icd_hcc = (
    df_method_metadata_inclusion
        .join(
            df_hcc_main,
            ((col("CLAIM_CD_TYPE")=='DIAGNOSIS') & (col("CLAIM_CD") == col("icd_hcc.diagnosiscode"))),
            "inner"
        )
        .select(
            col("METHOD_ID"), col("CLAIM_CD_TYPE"), col("CLAIM_CD"), col("icd_hcc.*")
        )
)

print("Method Metadata + HCC Count: ", df_method_icd_hcc.count())

# COMMAND ---------- Step 3: Joining facility and professional claims
df_facility_all = spark.sql(f"""
   SELECT f.CLAIM_BID, f.MEMBER_BID, f.CLM_PMT_STS_CD, f.CLM_TP_OF_BILL_CD,
          f.CLM_LOAD_MONTH, fdt.CLAIM_LN_NUM, fdt.CPT_AND_HCPCS_CD,
          f.DIAG_TYPE_CD, f.DIAG_CD, f.PRINC_PROC_CD
   FROM {catalog}.{schema}.facility f
   INNER JOIN {catalog}.{schema}.facility_detail fdt ON f.FACILITY_BID=fdt.FACILITY_BID
""")

df_professional_all = spark.sql(f"""
   SELECT p.PROFESSIONAL_BID, p.CLAIM_BID, p.MEMBER_BID,
          p.CLM_PMT_STS_CD, p.CLM_TP_CD, 
          pd.CLAIM_LN_NUM, pd.CPT_HCPCS_CD
   FROM {catalog}.{schema}.professional p
   INNER JOIN {catalog}.{schema}.professional_diag pd
       ON p.PROFESSIONAL_BID = pd.PROFESSIONAL_BID
""")
# COMMAND ----------
# gs_4

df_draft_gap_M1 = df_method_metadata_with_cc_code.alias("inc").join(
    df_pharmacy_claims.alias("RX_claim"),
    (
        (col("inc.CLAIM_CD_TYPE") == "NDC")
        & (col("inc.CLAIM_CD") == col("RX_claim.PROD_SERV_ID_CD"))
    ),
    "inner"
).select(
    col("inc.METHOD_ID"),
    col("inc.CLAIM_CD_TYPE"),
    col("inc.CLAIM_CD"),
    col("inc.CC_ID"),
    col("inc.PERCENT_WEIGHT"),
    col("inc.CC_CODE"),
    col("inc.DESCRIPTION"),
    col("inc.SAS_MODEL_YEAR"),
    col("inc.SAS_MODEL_VERSION"),
    col("inc.CLAIM_CD_MODIFIER_TYPE"),
    col("inc.CLAIM_CD_MODIFIER"),
    col("inc.EXCLUSION_TYPE_1"),
    col("inc.EXCLUSION_1"),
    col("inc.EXCLUSION_TYPE_2"),
    col("inc.EXCLUSION_2"),
    col("RX_claim.MEMBER_BID"),
    year(col("RX_claim.ANNUAL_SRV_DT")).alias("YEAR"),
    col("RX_claim.CLM_NUM").alias("CLM_NUM"),
    col("RX_claim.CLM_LINE_NBR").alias("CLM_LINE_NUM"),
    col("RX_claim.DIAG_CD_1"),
    col("RX_claim.DIAG_CD_2"),
    col("RX_claim.DIAG_CD_3"),
    col("RX_claim.DIAG_CD_4"),
    col("RX_claim.PAID_AMT"),
    col("RX_claim.CLM_ID"),
    lit("RX").alias("CLAIM_TYPE"),
    col("RX_claim.ADJUDICATION_DT").alias("MATCHED_DATE"),
    lit("Inclusion Logic").alias("SCENARIO_TYPE")
)

# COMMAND ----------
# DBTITLE 1, Inclusion Draft Gap - Methods 2 & 10 (Medical Claims)

from pyspark.sql.functions import col, year, lit

df_draft_gap_M2_10 = df_method_metadata_with_cc_code.alias("inc").join(
    df_final_medical_claims_all.alias("all_claim"),
    (
        ((col("inc.CLAIM_CD_TYPE") == "DIAGNOSIS") &
         (col("inc.CLAIM_CD") == col("all_claim.DIAG_CD")))
        |
        ((col("inc.CLAIM_CD_TYPE") == "CPT-HCPCS") &
         (col("inc.CLAIM_CD") == col("all_claim.CPT_AND_HCPCS_CD")))
        |
        ((col("inc.CLAIM_CD_TYPE") == "ICD-PROC") &
         (col("inc.CLAIM_CD") == col("all_claim.PRINC_PROC_CD")))
    ),
    "inner"
).select(
    col("inc.METHOD_ID"),
    col("inc.CLAIM_CD_TYPE"),
    col("inc.CLAIM_CD"),
    col("inc.CC_ID"),
    col("inc.PERCENT_WEIGHT"),
    col("inc.CC_CODE"),
    col("inc.DESCRIPTION"),
    col("inc.SAS_MODEL_YEAR"),
    col("inc.SAS_MODEL_VERSION"),
    col("inc.CLAIM_CD_MODIFIER_TYPE"),
    col("inc.CLAIM_CD_MODIFIER"),
    col("inc.EXCLUSION_TYPE_1"),
    col("inc.EXCLUSION_1"),
    col("inc.EXCLUSION_TYPE_2"),
    col("inc.EXCLUSION_2"),
    col("all_claim.MEMBER_BID"),
    col("all_claim.RISK_YEAR").alias("YEAR"),
    col("all_claim.CLM_NUM"),
    col("all_claim.CLM_LINE_NUM"),
    col("all_claim.DIAG_CD_1"),
    col("all_claim.DIAG_CD_2"),
    col("all_claim.DIAG_CD_3"),
    col("all_claim.DIAG_CD_4"),
    col("all_claim.PAID_AMT"),
    col("all_claim.CLM_ID"),
    lit("M").alias("CLAIM_TYPE"),
    lit("NA").alias("MATCHED_DATE"),
    lit("Inclusion Logic").alias("SCENARIO_TYPE")
)

df_inclusion_draft_gap = df_draft_gap_M1.union(df_draft_gap_M2_10)

print(f"Inclusion Draft Gap Count : {df_inclusion_draft_gap.count()}")

# COMMAND ----------
# gs_5
# DBTITLE 1, Exclusion Gap Suspecting - Scenario 1 (With Modifiers)

from pyspark.sql.functions import col, lit, datediff, year, when

df_ref_method_metadata = spark.table(f"{catalog}.{ma_reference}.ref_method_metadata")
df_ref_method_metadata_codegroups = spark.table(f"{catalog}.{ma_reference}.ref_method_metadata_codegroups")

df_scenario1_metadata = df_ref_method_metadata.filter(
    (col("PROGRAM") == "CMS")
    & (col("METHOD_ID").isin(1, 2, 10))
    & (col("EXCLUSION_TYPE_1") != "NA")
    & (col("CLAIM_CD_MODIFIER_TYPE") != "NA")
)

# S1: Find claims matching CPT-HCPCS codes
df_s1_claims = df_final_medical_claims_all.alias("all").join(
    df_scenario1_metadata.alias("meta"),
    (
        (col("meta.CLAIM_CD_TYPE") == "CPT-HCPCS")
        & (col("meta.CLAIM_CD") == col("all.CPT_AND_HCPCS_CD"))
    ),
    "inner"
).select(
    col("all.*"),
    col("meta.METHOD_ID"),
    col("meta.CLAIM_CD_MODIFIER_TYPE"),
    col("meta.CLAIM_CD_MODIFIER"),
    col("meta.EXCLUSION_TYPE_1"),
    col("meta.EXCLUSION_1"),
    col("meta.EXCLUSION_TYPE_2"),
    col("meta.EXCLUSION_2"),
    lit("Exclusion logic").alias("SCENARIO_TYPE")
)

print(f"S1 claims that matched the CPT codes: {df_s1_claims.count()}")
df_s1_claims.display()

# S2: Get procedures code for the modifier groups and check if at least one of them exist in the SAME claim
df_modifier_codes = df_ref_method_metadata_codegroups.join(
    df_scenario1_metadata.select(
        "CLAIM_CD_MODIFIER_TYPE",
        "CLAIM_CD_MODIFIER"
    ).distinct(),
    (df_ref_method_metadata_codegroups["CLAIM_CD_TYPE"] == col("CLAIM_CD_MODIFIER_TYPE"))
    & (df_ref_method_metadata_codegroups["CLAIM_CD"] == col("CLAIM_CD_MODIFIER")),
    "inner"
).select(
    "CODE",
    "CPT_AND_HCPCS_CD",
    "CLAIM_CD_MODIFIER_TYPE",
    "CLAIM_CD_MODIFIER"
)

df_modifier_codes.display()

# COMMAND ----------
# gs_6

# Join back to find claims with modifier codes in same claim
df_s2_claims = df_s1_claims.join(
    df_final_medical_claims_all.alias("modifier_check").select(
        col("modifier_check.CLM_BID").alias("modifier_check_CLM_BID"),
        col("modifier_check.CLM_TP_CD").alias("modifier_check_CLM_TP_CD"),
        col("modifier_check.CPT_AND_HCPCS_CD").alias("MODIFIER_CODE_FOUND")
    ),
    (df_s1_claims["CLM_BID"] == col("modifier_check_CLM_BID"))
    & (df_s1_claims["CLM_TP_CD"] == col("modifier_check_CLM_TP_CD")),
    "inner"
).join(
    df_modifier_codes,
    col("MODIFIER_CODE_FOUND") == df_modifier_codes["CODE"],
    "inner"
).select(
    df_s1_claims["*"],
    df_modifier_codes["CODE"],
    lit("Exclusion logic").alias("SCENARIO_TYPE")
).distinct()

print(f"S2 claims (with procedure code from modifier group in the same claim): {df_s2_claims.count()}")
df_s2_claims.display()

# S3: Get exclusion diagnosis codes and check in last 180 days for same member
df_exclusion_codes = df_ref_method_metadata_codegroups.join(
    df_scenario1_metadata.select(
        "EXCLUSION_TYPE_1",
        "EXCLUSION_1",
        "EXCLUSION_TYPE_2",
        "EXCLUSION_2"
    ).distinct(),
    (df_ref_method_metadata_codegroups["CLAIM_CD_TYPE"] == col("EXCLUSION_TYPE_1"))
    & (df_ref_method_metadata_codegroups["CLAIM_CD"] == col("EXCLUSION_1"))
    | (df_ref_method_metadata_codegroups["CLAIM_CD_TYPE"] == col("EXCLUSION_TYPE_2"))
    & (df_ref_method_metadata_codegroups["CLAIM_CD"] == col("EXCLUSION_2")),
    "inner"
).select(
    "CODE",
    "EXCLUSION_TYPE_1",
    "EXCLUSION_1",
    "EXCLUSION_TYPE_2",
    "EXCLUSION_2"
).distinct()

# COMMAND ----------
# gs_7

# Find exclusion diagnosis in last 180 days - capture the matched diagnosis code
df_s3_exclusions = df_s2_claims.join(
    df_final_medical_claims_all.alias("hist").select(
        col("hist.MEMBER_BID").alias("HIST_MEMBER_BID"),
        col("hist.CLM_ID").alias("HIST_CLM_ID"),
        col("hist.CLM_DT").alias("HIST_CLM_DT"),
        col("hist.DIAG_CD").alias("HIST_DIAG_CD")
    ),
    (df_s2_claims["MEMBER_BID"] == col("HIST_MEMBER_BID"))
    & (datediff(df_s2_claims["CLM_DT"], col("HIST_CLM_DT")) > 0)
    & (datediff(df_s2_claims["CLM_DT"], col("HIST_CLM_DT")) <= 180),
    "inner"
).join(
    df_exclusion_codes,
    col("HIST_DIAG_CD") == df_exclusion_codes["CODE"],
    "inner"
).select(
    df_s2_claims["*"],
    col("HIST_DIAG_CD").alias("MATCHED_CODE")
).distinct()

print(f"S3 claims with exclusions found in last 180 days: {df_s3_exclusions.count()}")
df_s3_exclusions.display()

# Final DataFrame: Mark records based on exclusion presence
# Create a unique identifier for joining - include MATCHED_CODE
df_s3_with_flag = df_s3_exclusions.select(
    "CLM_BID",
    "MEMBER_BID",
    "CLM_TP_CD",
    "CLM_ID",
    "CPT_AND_HCPCS_CD",
    "CODE",
    "DIAG_NUM",
    "DIAG_CD",
    "METHOD_ID",
    "CC_ID",
    "MATCHED_CODE"
).distinct().withColumn("EXCLUSION_FLAG", lit(1))

df_s3_with_flag.display()

# Left join to mark which records had exclusions
df_final_scenario1 = df_s2_claims.join(
    df_s3_with_flag.alias("s3"),
    (df_s2_claims["CLM_BID"] == col("s3.CLM_BID"))
    & (df_s2_claims["MEMBER_BID"] == col("s3.MEMBER_BID"))
    & (df_s2_claims["CLM_TP_CD"] == col("s3.CLM_TP_CD"))
    & (df_s2_claims["CLM_ID"] == col("s3.CLM_ID")),
    "left"
).select(
    df_s2_claims["*"],
    col("s3.MATCHED_CODE"),
    when(col("s3.EXCLUSION_FLAG") == 1,
         lit("Found Exclusion in 180 days")).alias("GAP_REASON"),
    when(col("s3.EXCLUSION_FLAG") == 1,
         lit("DO NOT Create Gap"))
    .otherwise(lit("Create Gap")).alias("GAP_STATUS")
)

print(f"Final Scenario 1 DataFrame with GAP_REASON and GAP_STATUS: {df_final_scenario1.count()}")
df_final_scenario1.display()

# COMMAND ----------
# gs_8

print("------ Scenario 1 Distinct Summary ------")
df_final_scenario1_summary = df_final_scenario1.select(
    "CLM_BID",
    "MEMBER_BID",
    "CLM_TP_CD",
    "CLM_ID",
    "CPT_AND_HCPCS_CD",
    "METHOD_ID",
    "CC_ID",
    "CODE",
    "MATCHED_CODE",
    "SCENARIO_TYPE",
    "GAP_REASON",
    "GAP_STATUS"
).distinct()

df_final_scenario1_summary.display()

print("------ Scenario 1 Gap Status Summary ------")
df_final_scenario1.groupby("GAP_STATUS", "GAP_REASON").count().display()

# COMMAND ----------
# DBTITLE 1, Exclusion Gap Suspecting - Scenario 2 (Without Modifiers)

from pyspark.sql.functions import col, lit, datediff, year, when

df_scenario2_metadata = df_ref_method_metadata.filter(
    (col("PROGRAM") == "CMS")
    & (col("METHOD_ID").isin(1, 2, 10))
    & (col("EXCLUSION_TYPE_1") != "NA")
    & (col("CLAIM_CD_MODIFIER_TYPE") == "NA")
)

# S1: Find claims matching CPT-HCPCS codes - Use alias for df_final_medical_claims_all
df_s1_claims_scenario2 = df_final_medical_claims_all.alias("claims").join(
    df_scenario2_metadata.alias("meta"),
    (
        (col("meta.CLAIM_CD_TYPE") == "CPT-HCPCS")
        & (col("meta.CLAIM_CD") == col("claims.CPT_AND_HCPCS_CD"))
    ),
    "inner"
).select(
    col("claims.*"),
    col("claims.CLM_DT").alias("RISK_YEAR"),
    col("meta.METHOD_ID"),
    col("meta.CLAIM_CD_TYPE"),
    col("meta.CLAIM_CD"),
    col("meta.CLAIM_CD_MODIFIER_TYPE"),
    col("meta.CLAIM_CD_MODIFIER"),
    col("meta.QUALIFIED_CLAIM"),
    col("meta.METHOD_DESCRIPTION"),
    col("meta.EXCLUSION_TYPE_1"),
    col("meta.EXCLUSION_1"),
    col("meta.EXCLUSION_TYPE_2"),
    col("meta.EXCLUSION_2"),
    lit("Exclusion logic").alias("SCENARIO_TYPE")
).distinct()

print(f"S1 claims (Scenario 2) that matched the CPT codes: {df_s1_claims_scenario2.count()}")
df_s1_claims_scenario2.display()

# COMMAND ----------
# gs_9

# S2: Get exclusion Diagnosis codes from method_metadata_group
df_exclusion_codes_scenario2 = df_ref_method_metadata_codegroups.alias("codegroups").join(
    df_scenario2_metadata.select(
        "MEMBER_BID",
        "EXCLUSION_TYPE_1",
        "EXCLUSION_1",
        "EXCLUSION_TYPE_2",
        "EXCLUSION_2"
    ).distinct().alias("excl"),
    (
        (col("codegroups.CLAIM_CD_TYPE") == col("excl.EXCLUSION_TYPE_1"))
        & (col("codegroups.CLAIM_CD") == col("excl.EXCLUSION_1"))
    )
    | (
        (col("codegroups.CLAIM_CD_TYPE") == col("excl.EXCLUSION_TYPE_2"))
        & (col("codegroups.CLAIM_CD") == col("excl.EXCLUSION_2"))
    ),
    "inner"
).select(
    col("excl.MEMBER_BID"),
    col("CODE"),
    col("EXCLUSION_TYPE_1"),
    col("EXCLUSION_1"),
    col("EXCLUSION_TYPE_2"),
    col("EXCLUSION_2")
).distinct()

df_exclusion_codes_scenario2.display()

# S3: Find exclusion diagnosis in last 180 days
df_s2_exclusions_scenario2 = df_s1_claims_scenario2.alias("claims").join(
    df_final_medical_claims_all.alias("hist").select(
        col("hist.MEMBER_BID").alias("HIST_MEMBER_BID"),
        col("hist.CLM_ID").alias("HIST_CLM_ID"),
        col("hist.CLM_DT").alias("HIST_CLM_DT"),
        col("hist.DIAG_CD").alias("HIST_DIAG_CD")
    ),
    (col("claims.MEMBER_BID") == col("HIST_MEMBER_BID"))
    & (datediff(col("claims.CLM_DT"), col("HIST_CLM_DT")) > 0)
    & (datediff(col("claims.CLM_DT"), col("HIST_CLM_DT")) <= 180),
    "inner"
).join(
    df_exclusion_codes_scenario2.alias("excl_codes"),
    col("HIST_DIAG_CD") == col("excl_codes.CODE"),
    "inner"
).select(
    col("claims.*"),
    col("excl_codes.CODE"),
    col("HIST_DIAG_CD").alias("MATCHED_CODE"),
    col("HIST_CLM_DT").alias("MATCHED_DATE")
).distinct()

print("df_s1_claims_scenario2-------------------")
df_s1_claims_scenario2.display()
print(f"S2 claims (Scenario 2) with exclusions found in last 180 days: {df_s2_exclusions_scenario2.count()}")
df_s2_exclusions_scenario2.display()

# COMMAND ----------
# gs_10

# Final DataFrame: Mark records based on exclusion presence
# Create a unique identifier for joining - use aliases to avoid ambiguity
df_s2_with_flag_scenario2 = df_s2_exclusions_scenario2.select(
    col("claims.CLM_BID").alias("CLM_BID"),
    col("claims.MEMBER_BID").alias("MEMBER_BID"),
    col("claims.CLM_TP_CD").alias("CLM_TP_CD"),
    col("claims.CLM_ID").alias("CLM_ID"),
    col("claims.CPT_AND_HCPCS_CD").alias("CPT_AND_HCPCS_CD"),
    col("CODE"),
    col("MATCHED_CODE"),
    col("MATCHED_DATE")
).distinct().withColumn("EXCLUSION_FLAG", lit(1))

df_s2_with_flag_scenario2.display()

# Left join to mark which records had exclusions - use aliases to avoid ambiguity
df_final_scenario2 = df_s1_claims_scenario2.alias("s1_all").join(
    df_s2_with_flag_scenario2.alias("s2_flagged"),
    (col("s1_all.CLM_BID") == col("s2_flagged.CLM_BID"))
    & (col("s1_all.MEMBER_BID") == col("s2_flagged.MEMBER_BID"))
    & (col("s1_all.CLM_TP_CD") == col("s2_flagged.CLM_TP_CD"))
    & (col("s1_all.CLM_ID") == col("s2_flagged.CLM_ID"))
    & (col("s1_all.CPT_AND_HCPCS_CD") == col("s2_flagged.CPT_AND_HCPCS_CD")),
    "left"
).select(
    col("s1_all.*"),
    col("s2_flagged.CODE"),
    col("s2_flagged.MATCHED_CODE"),
    col("s2_flagged.MATCHED_DATE"),
    when(col("s2_flagged.EXCLUSION_FLAG") == 1,
         lit("Found Exclusion in 180 days")).alias("GAP_REASON"),
    when(col("s2_flagged.EXCLUSION_FLAG") == 1,
         lit("DO NOT Create Gap"))
    .otherwise(lit("Create Gap")).alias("GAP_STATUS")
)

print(sorted(df_final_scenario2.columns))
print(f"Final Scenario 2 Dataframe with GAP_REASON and GAP_STATUS: {df_final_scenario2.count()}")
df_final_scenario2.display()

print("------ Scenario 2 Distinct Summary ------")
df_final_scenario2_summary = df_final_scenario2.select(
    "CLM_BID",
    "MEMBER_BID",
    "CLM_TP_CD",
    "CLM_ID",
    "CPT_AND_HCPCS_CD",
    "CODE",
    "MATCHED_CODE",
    "MATCHED_DATE",
    "SCENARIO_TYPE",
    "GAP_REASON",
    "GAP_STATUS"
).distinct()

df_final_scenario2_summary.display()

print("------ Scenario 2 Gap Status Summary ------")
df_final_scenario2.groupby("GAP_STATUS", "GAP_REASON").count().display()
# COMMAND ----------
# Final DataFrame: Mark records based on exclusion presence

# Create a unique identifier for joining
df_s2_with_flag_scenario2 = df_s2_exclusions_scenario2.select(
    "CLM_BID",
    "MEMBER_BID",
    "CLM_TP_CD",
    "CLAIM_DT",
    "CPT_AND_HCPCS_CD",
    "METHOD_ID",
    "CC_ID",
    "MATCHED_CODE",
    "MATCHED_DATE"
).distinct().withColumn("EXCLUSION_FLAG", lit(1))

df_s2_with_flag_scenario2.display()

# Left join to mark which records had exclusions
df_final_scenario2 = df_s1_claims_scenario2.join(
    df_s2_with_flag_scenario2,
    ["CLM_BID", "MEMBER_BID", "CLM_TP_CD", "CLAIM_DT", "CPT_AND_HCPCS_CD", "METHOD_ID", "CC_ID"],
    "left"
).select(
    df_s1_claims_scenario2["*"],
    df_s2_with_flag_scenario2["MATCHED_CODE"],
    df_s2_with_flag_scenario2["MATCHED_DATE"],
    df_s2_with_flag_scenario2["EXCLUSION_FLAG"],
    when(col("EXCLUSION_FLAG") == 1, lit("Found Exclusion in 180 days"))
        .otherwise(lit("No Exclusion in 180 days")).alias("GAP_REASON"),
    when(col("EXCLUSION_FLAG") == 1, lit("DO NOT Create Gap"))
        .otherwise(lit("Create Gap")).alias("GAP_STATUS")
)

print(f"Final Scenario 2 DataFrame with GAP_REASON and GAP_STATUS: {df_final_scenario2.count()}")
df_final_scenario2.display()

print('--------Scenario 2 Distinct Summary--------')
df_final_scenario2_summary = df_final_scenario2.select(
    "CLM_BID",
    "MEMBER_BID",
    "CLAIM_DT",
    "CLM_TP_CD",
    "CPT_AND_HCPCS_CD",
    "METHOD_ID",
    "CC_ID",
    "MATCHED_CODE",
    "MATCHED_DATE",
    "SCENARIO_TYPE",
    "GAP_REASON",
    "GAP_STATUS"
).distinct()
df_final_scenario2_summary.display()

print('\n--------Scenario 2 Gap Status Summary--------')
df_final_scenario2_summary.groupby("GAP_STATUS", "GAP_REASON").count().display()

# COMMAND ----------
# Exclusion draft gap (union scenario 1 & 2 already built as df_final_scenario1_gap, df_final_scenario2_gap)

df_exclusion_draft_gap = df_final_scenario1_gap.unionByName(df_final_scenario2_gap)

df_exclusion_draft_gap_with_cc_code = df_exclusion_draft_gap.join(
    df_cc_code_mapping,
    df_exclusion_draft_gap["CC_ID"] == df_cc_code_mapping["CC_ID"],
    "left_outer"
).select(
    df_exclusion_draft_gap["*"],
    df_cc_code_mapping["SAS_MODEL_VERSION"],
    df_cc_code_mapping["SAS_MODEL_YEAR"],
    df_cc_code_mapping["CC_CODE"],
    df_cc_code_mapping["CC_DESCRIPTION"]
).distinct()

print(f"Exclusion Draft Gap Count: {df_exclusion_draft_gap_with_cc_code.count()}")
print(sorted(df_inclusion_draft_gap.columns))
print(sorted(df_exclusion_draft_gap_with_cc_code.columns))
df_exclusion_draft_gap_with_cc_code.display()

# COMMAND ----------
# DBTITLE 1, Exclusion Draft Gap
from pyspark.sql.functions import col, lit

# Union both scenarios to create exclusion draft gap
df_final_scenario1_gap = df_final_scenario1.select([
    'ALLWD_AMT', 'CC_ID', 'CLAIM_BID', 'CLAIM_CD', 'CLAIM_CD_MODIFIER',
    'CLAIM_CD_MODIFIER_TYPE', 'CLAIM_CD_TYPE', 'CLAIM_DT', 'CLM_LN_NUM',
    'CLM_PMTS_STS_CD', 'CLM_TP_CD', 'CODE', 'CPT_AND_HCPCS_CD', 'DIAG_CD',
    'DIAG_NUM', 'DIAG_TYPE_CD', 'EXCLUSION_1', 'EXCLUSION_2',
    'EXCLUSION_TYPE_1', 'EXCLUSION_TYPE_2', 'GAP_REASON', 'GAP_STATUS',
    'MATCHED_CODE', 'MATCHED_DATE', 'MEMBER_BID', 'METHOD_ID',
    'PERCENT_WEIGHT', 'PRINC_PROC_CD', 'QUALIFIED_CLAIM', 'RISK_YEAR',
    'SOURCE_LOAD_MONTH', 'SCENARIO_TYPE', 'TOP_OF_BILL_CD',
    'INVALID_CPT_HCPCS', 'QUALITY_CLAIMS'
])

df_final_scenario2_gap = df_final_scenario2.select([
    'ALLWD_AMT', 'CC_ID', 'CLAIM_BID', 'CLAIM_CD', 'CLAIM_CD_MODIFIER',
    'CLAIM_CD_MODIFIER_TYPE', 'CLAIM_CD_TYPE', 'CLAIM_DT', 'CLM_LN_NUM',
    'CLM_PMTS_STS_CD', 'CLM_TP_CD', 'CODE', 'CPT_AND_HCPCS_CD', 'DIAG_CD',
    'DIAG_NUM', 'DIAG_TYPE_CD', 'EXCLUSION_1', 'EXCLUSION_2',
    'EXCLUSION_TYPE_1', 'EXCLUSION_TYPE_2', 'GAP_REASON', 'GAP_STATUS',
    'MATCHED_CODE', 'MATCHED_DATE', 'MEMBER_BID', 'METHOD_ID',
    'PERCENT_WEIGHT', 'PRINC_PROC_CD', 'QUALIFIED_CLAIM', 'RISK_YEAR',
    'SOURCE_LOAD_MONTH', 'SCENARIO_TYPE', 'TOP_OF_BILL_CD',
    'INVALID_CPT_HCPCS', 'QUALITY_CLAIMS'
])

df_exclusion_draft_gap = df_final_scenario1_gap.unionByName(df_final_scenario2_gap)

df_exclusion_draft_gap_with_cc_code = df_exclusion_draft_gap.join(
    df_cc_code_mapping,
    df_exclusion_draft_gap["CC_ID"] == df_cc_code_mapping["CC_ID"],
    "left_outer"
).select(
    df_exclusion_draft_gap["*"],
    df_cc_code_mapping["SAS_MODEL_VERSION"],
    df_cc_code_mapping["SAS_MODEL_YEAR"],
    df_cc_code_mapping["CC_CODE"],
    df_cc_code_mapping["CC_DESCRIPTION"]
).distinct()

print(f"Exclusion Draft Gap Count: {df_exclusion_draft_gap_with_cc_code.count()}")
print(sorted(df_inclusion_draft_gap.columns))
print(sorted(df_exclusion_draft_gap_with_cc_code.columns))
df_exclusion_draft_gap_with_cc_code.display()

# COMMAND ----------
# DBTITLE 1, Combined Draft Gap: Inclusion & Exclusion

print(sorted(df_inclusion_draft_gap.columns))
print(sorted(df_exclusion_draft_gap_with_cc_code.columns))

from pyspark.sql.functions import col, lit

# Select common columns plus unique columns from inclusion draft gap
# Union both dataframes
df_combined_draft_gap = df_inclusion_draft_gap.unionByName(df_exclusion_draft_gap_with_cc_code)

print(f"Combined Draft Gap Count (Inclusion + Exclusion): {df_combined_draft_gap.count()}")
df_combined_draft_gap.display()

print('\n-------Combined Draft Gap Summary by Scenario Type-------')
df_combined_draft_gap.groupby("SCENARIO_TYPE", "GAP_STATUS", "GAP_REASON") \
    .count() \
    .orderBy("SCENARIO_TYPE", "GAP_STATUS") \
    .display()

print('\n-------Combined Draft Gap Summary by Method-------')
df_combined_draft_gap.groupby("METHOD_ID", "CC_ID", "GAP_STATUS") \
    .count() \
    .orderBy("METHOD_ID", "CC_ID") \
    .display()

print('\n-------df_combined_draft_gap_summary Distinct Summary-------')
df_combined_draft_gap_summary = df_combined_draft_gap.select(
    "CLM_BID",
    "MEMBER_BID",
    "CLAIM_DT",
    "CLM_TP_CD",
    "CPT_AND_HCPCS_CD",
    "METHOD_ID",
    "CC_ID",
    "CODE",
    "MATCHED_CODE",
    "MATCHED_DATE",
    "SCENARIO_TYPE",
    "GAP_REASON",
    "GAP_STATUS"
).distinct()

print(df_combined_draft_gap_summary.count())
df_combined_draft_gap_summary.display()

print('\n-------Draft Gap Distinct Summary by Method-------')
df_combined_draft_gap_summary.groupby("SCENARIO_TYPE", "GAP_STATUS", "GAP_REASON") \
    .count() \
    .orderBy("SCENARIO_TYPE", "GAP_STATUS") \
    .display()

# COMMAND ----------
# DBTITLE 1, Risk Member HCCs
from pyspark.sql.functions import (
    col, explode, from_json, get_json_object, collect_list,
    max as spark_max, concat, lpad, lit, coalesce
)
from pyspark.sql.types import StringType

# Read the data
df = spark.sql(f"""
    SELECT RISK_MEMBER_ID,
           SPLIT(RISK_MEMBER_ID, '_')[0] AS MEMBER_ID,
           HOME_PLAN_ID_CD,
           RISK_MODEL_YEAR,
           RISK_MODEL_VERSION,
           YEAR_MONTH,
           DIAG_CD_TO_HCC_JSON_LIST
    FROM {catalog}.{schema_curation}.risk_member_output
""")

print(df.count())

# Extract and format CC codes with "CC" prefix and left-padded to 3 digits
# Handle both v24 and v28 versions dynamically
df_member_cc = df

for i in range(30):
    cc_col_name = f"CC_Code{i+1}"
    df_member_cc = df_member_cc.withColumn(
        cc_col_name,
        concat(
            lit("CC"),
            lpad(
                coalesce(
                    get_json_object(col("DIAG_CD_TO_HCC_JSON_LIST")[i], "$['CMS-HCC-Model-Category-v28']"),
                    get_json_object(col("DIAG_CD_TO_HCC_JSON_LIST")[i], "$['CMS-HCC-Model-Category-v24']")
                ),
                3,
                "0"
            )
        )
    )

display(df_member_cc)

# COMMAND ----------
# DBTITLE 1, member_bid
df_member_bid = spark.sql(
    f"select distinct BID, HOME_PLAN_ID_CD, MEMBER_ID_CD "
    f"from {catalog}.{schema}.member_id order by BID"
)
display(df_member_bid)

# COMMAND ----------
# DBTITLE 1, Risk Member HCCs with BID
df_member_cc_with_BID = df_member_cc.join(
    df_member_bid,
    (df_member_cc["HOME_PLAN_ID_CD"] == df_member_bid["HOME_PLAN_ID_CD"]) &
    (df_member_cc["MEMBER_ID"] == df_member_bid["MEMBER_ID_CD"]),
    "left_outer"
).select(
    df_member_bid["BID"].alias("MEMBER_BID"),
    df_member_cc["*"]
)

display(df_member_cc_with_BID)

# COMMAND ----------
# DBTITLE 1, Final Member GAPs with CC matching
from pyspark.sql.functions import when, col, lit

df_final_gap = df_draft_gap.join(
    df_member_cc_with_BID,
    (df_member_cc_with_BID["MEMBER_BID"] == df_draft_gap["MEMBER_BID"]) &
    (df_member_cc_with_BID["RISK_MODEL_YEAR"] == df_draft_gap["RISK_YEAR"]) &
    (
        (df_member_cc_with_BID["CC_Code1"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code2"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code3"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code4"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code5"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code6"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code7"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code8"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code9"]  == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code10"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code11"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code12"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code13"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code14"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code15"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code16"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code17"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code18"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code19"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code20"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code21"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code22"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code23"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code24"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code25"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code26"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code27"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code28"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code29"] == df_draft_gap["CC_CODE"]) |
        (df_member_cc_with_BID["CC_Code30"] == df_draft_gap["CC_CODE"])
    ),
    "left_outer"
).withColumn(
    "MATCHING_YN",
    when(df_member_cc_with_BID["MEMBER_BID"].isNotNull(), lit("Y")).otherwise(lit("N"))
).filter(
    df_draft_gap["MEMBER_BID"] != 0
).select(
    df_draft_gap["*"],
    col("MATCHING_YN")
)

display(df_final_gap)

# COMMAND ----------
# DBTITLE 1, Member Final GAPs Summary
df_final_gap_summary = (
    df_final_gap
        .filter(col("MATCHING_YN") == "N")
        .groupBy("MEMBER_BID", "METHOD_ID", "RISK_YEAR", "SAS_MODEL_VERSION", "CC_ID", "CC_CODE")
        .count()
        .withColumnRenamed("count", "Occurrence")
        .orderBy("Occurrence")
)

display(df_final_gap_summary)

# COMMAND ----------
# MAGIC %md
# MAGIC ##------------------End of Mini MVP--------------------
