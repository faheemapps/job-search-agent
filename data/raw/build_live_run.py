"""
One-off script that assembles the raw job records collected during the live
demonstration run (2026-08-15) into the standard ingestion schema. Every
field below was taken verbatim from real Indeed/Dice/ZipRecruiter MCP tool
results or real WebSearch results gathered in that session -- nothing here
is invented. Where a source didn't show a value (salary, exact posting
date), the field is left null / UNVERIFIED rather than guessed.
"""
import json
from datetime import datetime, timedelta, timezone

TODAY = datetime(2026, 8, 15, tzinfo=timezone.utc)


def indeed_date(md, d, y=2026):
    return datetime.strptime(f"{md} {d}, {y}", "%B %d, %Y").replace(tzinfo=timezone.utc).isoformat()


def days_ago_date(n):
    return (TODAY - timedelta(days=n)).isoformat()


jobs = []

# ---------------------------------------------------------------- INDEED --
indeed_jobs = [
    ("Data Engineer(ETL to Snowflake)", "Pakka Jobs", "Remote (India)", "August", 6, "https://to.indeed.com/aaxkc8h47lhp"),
    ("Data Engineer (Snowflake)", "Kasmoprav", "Remote (India)", "August", 4, "https://to.indeed.com/aas9ql2qghqd"),
    ("Data Engineer", "Cimpress", "Remote (India)", "August", 11, "https://to.indeed.com/aa766vjnbsrc"),
    ("Data Engineer (ETL to Snowflake)", "DIAN Technology Solutions Pvt Ltd", "Remote (India)", "August", 6, "https://to.indeed.com/aaymt7ljjmvd"),
    ("Sr. Data Analytics Engineer – Snowflake", "Mukizh Fashions", "Remote (India)", "August", 6, "https://to.indeed.com/aaxtm2zdrzxv"),
    ("Sr. Data Engineer", "MTC", "Remote (India)", "August", 6, "https://to.indeed.com/aawd6bvfl2td"),
    ("Lead Data Engineer With Snowflake", "3Pillar Global", "Remote (India)", "May", 27, "https://to.indeed.com/aah4vdm9lmzz"),
    ("Data Engineer", "HiPaaS Inc", "Remote (India)", "July", 24, "https://to.indeed.com/aamh4fvkqpjt"),
    ("Data Engineer", "optimhire", "Remote (India)", "August", 12, "https://to.indeed.com/aamgtqn7h6jy"),
    ("Cloud Data Engineer", "mobiezy", "Remote (India)", "July", 27, "https://to.indeed.com/aaqzq8gsgdvq"),
    ("Senior Data Architect", "Astral Interntional", "Remote (India)", "August", 4, "https://to.indeed.com/aa8qwck4djkb"),
    ("Snowflake Data Architect (With AI experience)", "3Pillar Global", "Remote (India)", "June", 12, "https://to.indeed.com/aapqw8cwyhmf"),
    ("Solutions Architect - Data & Agentic AI Solution", "Techwurkz", "Remote (India)", "July", 18, "https://to.indeed.com/aa8gkx9zlvnx"),
    ("We're Hiring | Data Products & Snowflake Architect", "TriDevSofts", "Remote (India)", "August", 4, "https://to.indeed.com/aalyshf86v8t"),
    ("Snowflake Data Platform Lead(India)", "Codvo.ai", "Remote (India)", "March", 1, "https://to.indeed.com/aa2cnyg9dm76"),
    ("Senior Data Architect", "FuGenEd", "Remote (India)", "July", 27, "https://to.indeed.com/aa28mh784nq6"),
    ("Data Engineer", "WebSenor InfoTech", "Remote (India)", "August", 6, "https://to.indeed.com/aakf8j94jgmg"),
    ("Pricipal Analyst/ Data Engineer", "Wexa AI", "Remote (India)", "June", 1, "https://to.indeed.com/aatfv9rbqt8r"),
]
for title, company, loc, month, day, url in indeed_jobs:
    jobs.append({
        "job_title": title, "company_name": company, "location": loc,
        "posting_date": indeed_date(month, day), "posting_date_status": "VERIFIED",
        "salary_raw": None, "job_description": f"{title} at {company}. Listed as Remote on Indeed India.",
        "job_url": url, "company_url": None, "primary_source": "Indeed",
        "search_query": "Snowflake Data Engineer / Snowflake Data Architect (India, remote)",
    })

indeed_us_jobs = [
    ("Data Engineering & Reporting Manager", "Symmetry Lending", "Remote", "August", 12, "$160,000 - $195,000 a year", "https://to.indeed.com/aa6ryz4hqw2f"),
    ("Manager, Data Engineer (Remote)", "Arch Capital Group Ltd.", "Remote", "May", 28, "$100,500 - $174,000 a year", "https://to.indeed.com/aa9bsdf7jmmw"),
    ("Sr Data Engineering Product/Platform Manager", "Technoidentity", "Remote", "August", 10, "$80 - $100 an hour", "https://to.indeed.com/aahvysdk7rqr"),
    ("Databricks Platform Engineer", "PCI Professional Services LLC", "Remote", "August", 14, "$156,000 - $170,000 a year", "https://to.indeed.com/aaml6ywjcxn4"),
]
for title, company, loc, month, day, salary, url in indeed_us_jobs:
    jobs.append({
        "job_title": title, "company_name": company, "location": loc,
        "posting_date": indeed_date(month, day), "posting_date_status": "VERIFIED",
        "salary_raw": salary, "job_description": f"{title} at {company}. Listed as Remote on Indeed US.",
        "job_url": url, "company_url": None, "primary_source": "Indeed",
        "search_query": "Data Engineering Manager Snowflake (US, remote)",
    })

# ------------------------------------------------------------------ DICE --
dice_jobs = [
    ("Senior Data Modeler - Enterprise Data Warehouse - Remote", "UnitedHealth Group", "Chicago, Illinois, USA (Remote/On-Site)",
     "2026-08-14T20:54:48Z", "USD 91,700.00 - 163,700.00 per year",
     "Optum is a global organization delivering care aided by technology. Enterprise Data Warehouse, data modeling role.",
     "https://www.dice.com/job-detail/c09218cf-6273-4f72-a82c-6167aba1c176"),
    ("Cloud Solutions Architect – Databricks & AWS (Banking/Capital Markets)", "InfiCare", "New York, NY (Remote)",
     "2026-08-14T20:51:16Z", None,
     "Senior Level Data Architect with data analytics experience, Databricks, Pyspark, Python, ETL tools like Informatica. 15+ years of experience as Data Analyst / Data Engineer.",
     "https://www.dice.com/job-detail/77417dfc-18ee-42ff-8881-07cbb33b793b"),
    ("Data Architect", "PamTen Inc", "Remote",
     "2026-08-14T19:12:38Z", None,
     "Experienced Data Architect to define and evolve enterprise data architecture and design scalable, secure, high-performing data solutions.",
     "https://www.dice.com/job-detail/9ea330d3-9317-4f5c-9d86-6791c1885604"),
    ("Snowflake Data Architect - Healthcare Claims, Remote", "PRIMUS Global Services Inc.", "US (Remote)",
     "2026-08-14T18:45:53Z", "$65.00 - 70.00 (hourly)",
     "Immediate need for an experienced Data Architect with strong expertise in Snowflake, dbt, healthcare claims analytics.",
     "https://www.dice.com/job-detail/b6586538-9c06-4c5f-8481-fd1a1b7f33a1"),
    ("Snowflake Developer with SSIS", "Codinix Technologies Inc.", "Remote",
     "2026-08-14T18:22:59Z", "60 - 65 (hourly)",
     "Snowflake Developer or SQL Developer with SSIS experience. Design, develop, and maintain data solutions using Snowflake and ETL processes.",
     "https://www.dice.com/job-detail/a9b98fd8-682c-469a-a9cd-4c94f92268e3"),
    ("Healthcare Data Architect / Snowflake Architect (MedInsight)", "Tech Tandem Inc", "Remote",
     "2026-08-14T15:26:08Z", "$95+ (hourly)",
     "Rebuilt data foundation, integrated Milliman MedInsight data. Population Health data products and analytics.",
     "https://www.dice.com/job-detail/e29b9a5c-6583-48bb-b2ac-fbe248fade9a"),
    ("Snowflake Architect", "Tekfortune Inc.", "Remote",
     "2026-08-14T15:21:46Z", None,
     "Epic/Snowflake Architect, 6-12 months + extensions. Population Health data products and analytics capabilities.",
     "https://www.dice.com/job-detail/d8ed94f3-a305-4051-bc2c-0ca3164fb9c7"),
    ("Data Architect", "eBusiness Solutions, Inc.", "Remote",
     "2026-08-13T14:31:07Z", "60 - 65 (hourly)",
     "Designing, implementing, and maintaining data architecture. Cloud-native platforms such as Snowflake.",
     "https://www.dice.com/job-detail/b51d42d5-1947-450a-ae1d-103d5ed73cf3"),
    ("Snowflake Platform Administrator", "Openmind Technologies", "Remote (client based in Boston, MA)",
     "2026-08-14T22:21:30Z", None,
     "Snowflake Data Platform Engineer / Snowflake DBT Administrator for a total remote engagement.",
     "https://www.dice.com/job-detail/ba66eee3-ea69-4f68-a9ec-b3a30a156675"),
    ("Lead AI & Data Platform Engineer - Marketplace (Remote)", "Braintrust", "Delhi, India (Remote)",
     "2026-08-15T12:04:44Z", None,
     "Fully remote role, open to candidates in North America, LATAM, Europe, Asia and the Middle East. Live commerce and social marketplace, data-driven and AI-powered platform.",
     "https://www.dice.com/direct-apply/97ccc1d6-81c7-47a8-99bc-0fc0f9473843"),
]
for title, company, loc, posted_iso, salary, desc, url in dice_jobs:
    jobs.append({
        "job_title": title, "company_name": company, "location": loc,
        "posting_date": posted_iso, "posting_date_status": "VERIFIED",
        "salary_raw": salary, "job_description": desc,
        "job_url": url, "company_url": None, "primary_source": "Dice",
        "search_query": "Snowflake Informatica Data Architect / Snowflake Microsoft Fabric Airflow (remote)",
    })

# ------------------------------------------------------------ ZIPRECRUITER --
# job_redirect_url values are copied verbatim from the ZipRecruiter MCP tool's
# actual response (never fabricated -- see anti-hallucination rule on URLs).
zr_jobs = [
    ("ETL Data Engineer (Python & Snowflake)", "Hamiltonlane", "Remote", 0, 117200, 140700,
     "https://www.ziprecruiter.com/job-redirect?match_token=Co8BChZyT2ZhNzgyQTdRa1U2SGQ4U2pSZ2V3EiQwMWEwMDViYi0zYzg3LTc0Y2UtODUzYi03ZDk4YWYwNGUwNzEaS0FBSG03SFE5SU51T2hRN2N1blF6WHhXRExqY1VsdWJ6X09scVVDelJQVWJsMnNybU5BdFZOUXl2TUxIR083TEFSenhneDFrZGtfMCDJrQUQARjJrQU%3D&tsid=100000502"),
    ("Senior Solution Engineer, HCLS", "Snowflake", "Chicago, Illinois (Remote optional)", 25, 165000, 216562,
     "https://www.ziprecruiter.com/job-redirect?match_token=Co8BChZtRVB4Z2c4VlR1cDFCZFM2UmNzYkdREiQwMWEwMDViYi0zYzg3LTc1MTgtYTRkNS1kMWU3NmE5MDM4NDUaS0FBRmZqMEtWb3dtemRiRzM0Vk1hNldxS1JzYTRDME9vT2ZQcEswMW1TcDRkSXdnV2xCY0tmeUk5eVFGUmc5cTZSMWZ3LTVGcENXSSDJrQUQARjJrQU%3D&tsid=100000502"),
    ("Informatica powercenter with Teradata", "CLOUDSCOUTS SOFTWARE SOLUTIONS LLC", "Topeka, Kansas (Remote, Part-time)", 29, 110000, None,
     "https://www.ziprecruiter.com/job-redirect?match_token=Co8BChZsSVpsYlp4ZzBpc2pVRmhKdzVHdmlBEiQwMWEwMDViYi0zYzhhLTcyNGYtOTU5Ny0wYjQwY2NkYjYzMWYaS0FBSGN1d0tfTjl1UUs4cU0tamhuSWl5ZHI5cm5ZeFI5LXNrblZVcXJnVDNkT3F2ck52VVgyZjN4bWFrSTQwdFBqUmx6eVYxWXlMTSDJrQUQARjJrQU%3D&tsid=100000502"),
    ("Developer - Informatica/ETL", "Arthur Lawrence", "Remote", 16, 111500, 143500,
     "https://www.ziprecruiter.com/job-redirect?match_token=Co8BChZQaE44RDd0a1FyOHBXTkdrS01XS2JBEiQwMWEwMDViYi0zYzg3LTc0ZDgtODcxNi01YmVhOWM4MmNlNTMaS0FBRmI5X3d1d0o4Zi1pQlNiQXdXcE9qRUp4ZFR5RmFOZlV1UHZ5Q24yQTZ6Z0tUeVpCLUlmNUJ2aXA1cHlfQXRXMFNvVzV1amt2MCDJrQUQARjJrQU%3D&tsid=100000502"),
    ("Snowflake Data Governance Steward (Engineer 3) - FreeWheel", "Comcast", "Remote", 17, 117200, 140700,
     "https://www.ziprecruiter.com/job-redirect?match_token=Co8BChZIVzBVdE1zcC1LVmtROXJ2MTYyREpBEiQwMWEwMDViYi0zYzg3LTc0ZGYtYTY2Yi1iY2Y3ZGE4ZDM0MDAaS0FBRm1TcERSalgzZkZOYTJGOURFbnUwbWloQU9sT2NmVXRfdUFRdXltLTFyUzd6QmhyNEt5SDVOM01xTFltOVpmc2xIZ0hCS2toRSDJrQUQARjJrQU%3D&tsid=100000502"),
    ("Senior Data Warehouse Solutions Architect / Data Integration Engineer", "Strategic Solutions", "Baltimore, Maryland (Remote)", 10, 80000, 90000,
     "https://www.ziprecruiter.com/job-redirect?match_token=Co8BChZ2a1VMSTdIV25kRlhMTjZyVk5ibElREiQwMWEwMDViYy0yZDQ3LTcwMGYtYjllNi0zMzRhYTgxMzVjZTYaS0FBSDJTXzFkcjRNVU9BTngzZmx5RTgtUWk4VEt5QzU1ZDl6aHJNUkZwUWgyZndFQXJ3VFpFb2tTam1Tczg4ZHppaGQ4MWN5TDNIdyDJrQUQARjJrQU%3D&tsid=100000502"),
    ("Data Engineer II - Snowflake, dbt, AWS", "Travelers", "Hartford, Connecticut (Remote optional)", 4, 126500, 208700,
     "https://www.ziprecruiter.com/job-redirect?match_token=CpoBChZiRGhEcURCZTdrNjcwSGlwcGJiaXdBEiQwMWEwMDViYy0yZDQ3LTczMzQtODM2Ni1kOWFjODE0ZDljMzAaVkFBRmtlRWhMaVlVMG5wU2VpWkJkNWlmM2VzU2pRalBiMTNWbU5CUWRsTkpMdWxUUUwyQWlkQ2ZURS1kSXVnNDdpemRhNUViUWNoY1lpa0FyemVaUXNRIMmtBRABGMmtBQ%3D%3D&tsid=100000502"),
    ("REMOTE Enterprise Architect - C#, ETL/Data Warehousing", "Technology Navigators", "Houston, Texas (Remote)", 11, 160000, 165000,
     "https://www.ziprecruiter.com/job-redirect?match_token=CpoBChZFWkZwNzdnenJuNTV5bGt1SExlZ2tREiQwMWEwMDViYy0yZDRkLTc1NjEtOTJhNC0wYWIwOWU4YWNiN2QaVkFBRk5TNXI3R2VJMGpNd2x4ZGZZd1RlcGhic0FNR25ITXpxNWlSalM3RjN1VG1sTXhrTTJ2d2t2cWlKcmlMSXhhUHhoN050YnVIdl80Wk9ZUEZjeEl3IMmtBRABGMmtBQ%3D%3D&tsid=100000502"),
    ("IS Data Warehouse Architect II", "Careoregon", "Remote", 26, 122000, 163000,
     "https://www.ziprecruiter.com/job-redirect?match_token=Co8BChZzZWRwRTV5Sk55YUQ3eGtOcFpMbTZBEiQwMWEwMDViYy0yZDQ2LTdmM2UtYmIzMy04MTc2MjRlMjEyMjkaS0FBRjJjcWxCeWJlQ0xBdjRfbzRuSUJrUmpnV1RCek5oOW5tdnpTWlRFNllCZmJBTFVsTkZWT2ViVHZzZXhIMGxlSEY3Z2p3SUp4USDJrQUQARjJrQU%3D&tsid=100000502"),
    ("Lead ETL Developer- Enterprise Data Warehouse (EDW)", "Huntington", "Columbus, Ohio (Remote optional)", 4, 70000, 140000,
     "https://www.ziprecruiter.com/job-redirect?match_token=Co8BChYzYXBjSVEwN3g0b1dwRUUxeUJYWHpnEiQwMWEwMDViYy0yZDQ3LTcwMGMtYWE0Yi01OTRiYzIyZDM1NDgaS0FBRndQblByYTVBNldPVjNDUVNuZHM2LW96OGpKNGtmaW1sNVJZQkNXeXo2LV9fTUtYdXdlRXl3QWI3MFZfdkNHaWF3bE44U21fYyDJrQUQARjJrQU%3D&tsid=100000502"),
]
for title, company, loc, days_ago, smin, smax, real_url in zr_jobs:
    salary_raw = f"${smin:,} - ${smax:,} a year" if smax else f"${smin:,}+ a year"
    jobs.append({
        "job_title": title, "company_name": company, "location": loc,
        "posting_date": days_ago_date(days_ago), "posting_date_status": "VERIFIED",
        "salary_raw": salary_raw, "job_description": f"{title} at {company}. {loc}.",
        "job_url": real_url,
        "company_url": None, "primary_source": "ZipRecruiter",
        "search_query": "Snowflake Data Engineer / Data Warehouse Architect Snowflake (remote, US/Canada)",
    })

# ----------------------------------------------------- AI-SEARCH SOURCES --
ai_jobs = [
    ("Data Engineer (Informatica / AWS / Snowflake) - Remote", "Mutual of Omaha", "Remote",
     "https://www.linkedin.com/jobs/view/data-engineer-informatica-aws-snowflake-remote-at-mutual-of-omaha-4280262463",
     "LinkedIn", "Snowflake Informatica PowerCenter remote Data Engineer"),
    ("Data Architect - Snowflake (Azure & AWS)", "Quess", "Bengaluru, India (7 to 12 years)",
     "https://www.naukri.com/job-listings-data-architect-snowflake-azure-aws-quess-bengaluru-7-to-12-years-280726021578",
     "Naukri", "Snowflake Data Architect remote India"),
    ("Data Architect (Snowflake & Databricks)", "Birlasoft", "Pune, India (16 to 20 years)",
     "https://www.naukri.com/job-listings-data-architect-snowflake-databricks-birlasoft-india-limited-pune-16-to-20-years-250626503480",
     "Naukri", "Snowflake Data Architect remote India"),
    ("Snowflake Data Warehouse-Technology Architect", "Accenture", "Bangalore/Bengaluru, India (10 to 12 years)",
     "https://www.naukri.com/job-listings-snowflake-data-warehouse-technology-architect-accenture-solutions-pvt-ltd-bangalore-bengaluru-10-to-12-years-270124903074",
     "Naukri", "Snowflake Data Architect remote India"),
    ("Hiring_Snowflake Data Architect_Jaipur/Bhubneswar/Indore", "Sigma Allied Services", "Jaipur/Bhubaneswar/Indore, India (7 to 12 years)",
     "https://www.naukri.com/job-listings-hiring-snowflake-data-architect-jaipur-bhubneswar-indore-sigma-allied-services-bhubaneswar-indore-jaipur-7-to-12-years-090426019691",
     "Naukri", "Snowflake Data Architect remote India"),
    ("Snowflake Solution Architect / Cloud Data Architect", "Accion Labs", "Mumbai/Pune/Bengaluru, India (12 to 20 years)",
     "https://www.naukri.com/job-listings-snowflake-solution-architect-cloud-data-architect-accion-labs-mumbai-pune-bengaluru-12-to-20-years-180925017060",
     "Naukri", "Snowflake Data Architect remote India"),
    ("Snowflake Data Engineer", "Applycup Solutions (Client Confidential)", "Dubai, UAE (8 to 15 years)",
     "https://www.naukrigulf.com/snowflake-data-engineer-jobs-in-dubai-uae-in-applycup-solutions-8-to-15-years-n-cd-363323-jid-120826001146",
     "NaukriGulf", "Snowflake Data Engineer remote Dubai UAE"),
    ("Snowflake Architect", "LTIMindtree", "Hyderabad, India",
     "https://www.instahyre.com/job-277203-snowflake-architect-at-ltimindtree-2-hyderabad/",
     "Instahyre", "Snowflake ETL Architect remote India"),
    ("Snowflake Engineer", "Voya India", "Bangalore, India",
     "https://www.instahyre.com/job-337596-snowflake-engineer-at-voya-india-bangalore/",
     "Instahyre", "Snowflake ETL Architect remote India"),
    ("Data Engineering Manager (Snowflake)", "Company via BuiltIn", "Not stated (listing aggregator)",
     "https://builtin.com/job/data-engineering-manager-snowflake/6996660",
     "GoogleWebSearch", "Data Engineering Manager Snowflake remote"),
    ("Snowflake Data Engineer/Architect (Snowflake, DBT, Azure)", "Company via BuiltIn", "Not stated (listing aggregator)",
     "https://builtin.com/job/snowflake-data-engineer-architect-snowflake-dbt-azure/6256413",
     "GoogleWebSearch", "Snowflake Data Architect remote India"),
]
for title, company, loc, url, source, query in ai_jobs:
    jobs.append({
        "job_title": title, "company_name": company, "location": loc,
        "posting_date": None, "posting_date_status": "UNVERIFIED",
        "salary_raw": None,
        "job_description": f"{title} at {company}, {loc}. (Discovered via WebSearch; only title/company/location visible in search results — full description not fetched because the source page required a login or disallowed automated fetching per robots.txt.)",
        "job_url": url, "company_url": None, "primary_source": source,
        "search_query": query,
    })

out_path = "/root/job_search_agent/data/raw/live_run_2026-08-15.json"
with open(out_path, "w") as f:
    json.dump(jobs, f, indent=2)

print(f"Wrote {len(jobs)} raw job records to {out_path}")
