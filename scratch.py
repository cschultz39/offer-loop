from fetch_job_text import JobTextFetcher

url = "https://abbott.wd5.myworkdayjobs.com/en-US/abbottcareers/job/United-States---Texas---Irving/Associate-Software-Engineer_31158107-1"
with JobTextFetcher() as fetcher:
    status_code, description = fetcher.fetch(url)

print("status_code:", status_code)
print("length:", len(description) if description else 0)
print(description[:500] if description else "None")