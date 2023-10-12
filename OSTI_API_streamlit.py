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
        "start": start_index,  # Starting index for the batch
        "rows": batch_size  # Number of results per batch
    }
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        st.warning(f"Request for DOI {doi} batch {batch_number} failed with status code {response.status_code}")
        return None

# Convert JSON to CSV
def json_to_csv(data):
    output = StringIO()

    # Collect all possible field names from data
    all_keys = set()
    for record in data:
        row = record[0] if isinstance(record, list) else record
        all_keys.update(row.keys())
    fields = list(all_keys)

    # Remove 'links' if present and add separate fields for links
    if "links" in fields:
        fields.remove("links")
    fields.extend(["citation_link", "fulltext_link"])

    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()

    for record in data:
        row = record[0] if isinstance(record, list) else record

        # Flatten lists into comma-separated strings
        for key, value in row.items():
            if isinstance(value, list) and key != "links":
                row[key] = ', '.join(value)

        # Process links
        for link in row.get("links", []):
            if link["rel"] == "citation":
                row["citation_link"] = link["href"]
            elif link["rel"] == "fulltext":
                row["fulltext_link"] = link["href"]
        row.pop("links", None)  # Remove original links field

        writer.writerow(row)

    return output.getvalue()

def main():
    st.title("OSTI Query for DOIs")
    
    # Allow users to upload a DOI file
    uploaded_file = st.file_uploader("Upload a plain text file of DOIs. If the DOI is found in the public OSTI database, you will receive complete metadata for the record.", type=["txt"])
    
    if uploaded_file:
        # Read DOIs from the uploaded file
        file_content = uploaded_file.read()
        dois = read_dois_from_file(file_content)
        
        # Create a list to store the results
        results = []

        # List to store failed DOIs
        failed_dois = []

        # File to store the cumulative results
        cumulative_csv = StringIO()

        # Display a progress bar for user feedback
        progress_bar = st.progress(0)
        
        with st.spinner("Querying the public API..."):
            for index, doi in enumerate(dois):
                batch_number = 1
                has_data_for_doi = False  # Flag to check if there's any data for the current DOI
                
                while True:  # Loop to handle batches
                    result = query_api_with_doi(doi, batch_size=100, batch_number=batch_number)
                    
                    if not result or not result:  # if result is empty or None
                        break

                    results.extend(result)
                    
                    # Convert batch results to CSV and append
                    batch_csv_data = json_to_csv([result])
                    cumulative_csv.write(batch_csv_data)

                    # Indicate that we have data for this DOI
                    has_data_for_doi = True

                    # Check for the end of batches. Modify this if the API signals end of records differently.
                    if len(result) < 100:  # Less than 100 means this was the last batch
                        break

                    batch_number += 1

                # If no data was found for this DOI, add it to failed_dois list
                if not has_data_for_doi:
                    failed_dois.append(doi)
                
                # Update progress bar
                progress_bar.progress((index + 1) / len(dois))
            
        # Display failed DOIs
        if failed_dois:
            st.warning(f"The following DOIs were not found:")
            for doi in failed_dois:
                st.write(doi)

        # Preview the data for the user
        if results:
            preview_data = [record[0] if isinstance(record, list) else record for record in results]
            st.dataframe(preview_data)
            
            # Let users download the cumulative results as CSV
            st.download_button("Download your results", data=cumulative_csv.getvalue().encode(), file_name="api_results.csv", mime="text/csv")
        else:
            st.warning("No results obtained.")

if __name__ == '__main__':
    main()

