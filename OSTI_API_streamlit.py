import streamlit as st
import requests
import json
import csv
from io import StringIO

# Define the API endpoint you want to query
api_url = "https://www.osti.gov/api/v1/records"

# Function to read DOIs from a text file
def read_dois_from_file(file_content):
    return [line.strip() for line in file_content.decode("utf-8").splitlines()]

# Function to query the API with a DOI
def query_api_with_doi(doi, batch_size=100, batch_number=1):
    start_index = (batch_number - 1) * batch_size
    params = {
        "doi": doi,
        "start": start_index,
        "rows": batch_size
    }
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        # Ensure that data is a dictionary
        if isinstance(data, list):
            return {'results': data}
        return data
    else:
        st.warning(f"Request for DOI {doi} batch {batch_number} failed with status code {response.status_code}")
        return None

# Convert JSON to CSV
def json_to_csv(data, include_header=True):
    output = StringIO()

    # Collect all possible field names from data
    all_keys = set()
    for record in data:
        row = record[0] if isinstance(record, list) else record
        all_keys.update(row.keys())
    fields = list(all_keys)

    writer = csv.DictWriter(output, fieldnames=fields)
    if include_header:
        writer.writeheader()

    for record in data:
        row = record[0] if isinstance(record, list) else record
        
        # Ensure every record contains all the fieldnames
        for field in fields:
            if field not in row:
                row[field] = "none"  # or row[field] = "" if you prefer empty cells for missing values

        writer.writerow(row)

    return output.getvalue(), fields

def main():
    st.title("OSTI Query for DOIs")
    uploaded_file = st.file_uploader("Upload a plain text file of DOIs. If the DOI is found in the public OSTI database, you will receive complete metadata for the record.", type=["txt"])
    
    if uploaded_file:
        file_content = uploaded_file.read()
        dois = read_dois_from_file(file_content)
        results = []
        failed_dois = []
        cumulative_csv = StringIO()
        first_batch = True
        progress_bar = st.progress(0)
        
        with st.spinner("Querying the public API..."):
            for index, doi in enumerate(dois):
                batch_number = 1
                has_data_for_doi = False
                while True:
                    result = query_api_with_doi(doi, batch_size=100, batch_number=batch_number)
                    if not result or 'results' not in result or not result['results']:
                        break
                    results.extend(result.get('results', []))
                    has_data_for_doi = True
                    if len(result.get('results', [])) < 100:
                        break
                    batch_number += 1
                if not has_data_for_doi:
                    failed_dois.append(doi)
                progress_bar.progress((index + 1) / len(dois))
            
        if failed_dois:
            st.warning("The following DOIs were not found:")
            for doi in failed_dois:
                st.write(doi)

        # Convert the entire results set to CSV at once
        if results:
            cumulative_csv_data, headers = json_to_csv(results, include_header=True)
            cumulative_csv.write(cumulative_csv_data)
            preview_data = [record[0] if isinstance(record, list) else record for record in results]
            st.dataframe(preview_data)
            st.download_button("Download your results", data=cumulative_csv.getvalue().encode(), file_name="api_results.csv", mime="text/csv")
        else:
            st.warning("No results obtained.")

if __name__ == '__main__':
    main()
