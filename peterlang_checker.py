import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from io import BytesIO
import time

# Sidebar Navigation
st.sidebar.title("📘 Navigation")
page = st.sidebar.radio("Go to", ["Peter Lang Checker", "How to Use"])

# Instructions Page
if page == "How to Use":
    st.title("🧾 How to Use the Peter Lang Book Checker")
    st.markdown("""
    ### 📂 Step-by-step Instructions

    1. **Prepare your Excel (.xlsx)** file with columns such as:
       - `Author Name`
       - `ISBN`
       - `Book Title`
       - `Publication Date` (optional)

    2. **Upload your Excel file** on the checker page.

    3. **Map the columns** appropriately.

    4. **Click 'Check Availability'** to start the check.

    5. **View results** (Availability, Search URL, Final URL) live.

    6. **Download** results as CSV or Excel.

    ### 📬 Need Help?
    For feedback or issues: **📧 sm1043@gmail.com**
    """)
    st.stop()

# Main App
st.title("📚 Peter Lang Book Availability Checker")
uploaded_file = st.file_uploader("Upload Excel file (xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ File uploaded successfully!")

    with st.expander("🔧 Map Your Columns"):
        columns = df.columns.tolist()
        author_col = st.selectbox("Select Author Name column", columns)
        isbn_col = st.selectbox("Select ISBN column", columns)
        book_col = st.selectbox("Select Book Name column", columns)
        date_col = st.selectbox("Select Publication Date column (optional)", ["None"] + columns)

    def search_peterlang(row):
        base_url = "https://www.peterlang.com/search?searchstring="
        isbn = str(row.get(isbn_col, "")).strip()
        author = str(row.get(author_col, "")).strip()
        book = str(row.get(book_col, "")).strip()

        if isbn and isbn.lower() != "nan":
            query = isbn
        elif author and book:
            query = f"{author} {book}"
        elif book:
            query = book
        else:
            return pd.Series(["Not Available", "No valid input", ""])

        search_url = base_url + quote_plus(query)
        st.write(f"🔎 Searching: [{query}]({search_url})")

        try:
            response = requests.get(search_url, timeout=15, allow_redirects=True)
            final_url = response.url

            if "/document/" in final_url:
                try:
                    doc_page = requests.get(final_url, timeout=10)
                    doc_soup = BeautifulSoup(doc_page.text, 'html.parser')
                    details = doc_soup.find('div', class_='document__details') or doc_soup
                    text_content = details.get_text()
                    if isbn.replace("-", "") in text_content.replace("-", ""):
                        st.write(f"✅ Book matched via redirect and validated: [{final_url}]({final_url})")
                        return pd.Series(["Available", search_url, final_url])
                    else:
                        st.warning(f"⚠️ Redirected but ISBN mismatch: {final_url}")
                        return pd.Series(["Not Available", search_url, final_url])
                except Exception as e:
                    st.error(f"⚠️ Error validating redirect page: {e}")
                    return pd.Series(["Error", search_url, final_url])

            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('div', class_='product-details')

            for result in results:
                link_tag = result.find('a', href=True)
                if (isbn and isbn in result.text) or (book and book.lower() in result.text.lower()):
                    if link_tag:
                        book_url = "https://www.peterlang.com" + link_tag['href']
                        st.write(f"✅ Book found in search results: [{book_url}]({book_url})")
                        return pd.Series(["Available", search_url, book_url])
            st.warning(f"❌ Book not found for: [{query}]({search_url})")
            return pd.Series(["Not Available", search_url, ""])

        except Exception as e:
            st.error(f"❌ Error searching {query}: {e}")
            return pd.Series(["Error", search_url, ""])

    if st.button("🔍 Check Availability"):
        st.subheader("🔗 Live Search Status")
        progress_bar = st.progress(0)
        status_text = st.empty()

        results = []
        total_rows = len(df)

        with st.spinner("🚀 Searching Peter Lang..."):
            for i, row in df.iterrows():
                result = search_peterlang(row)
                results.append(result)
                progress = int((i + 1) / total_rows * 100)
                progress_bar.progress(progress)
                status_text.text(f"Processed {i + 1} of {total_rows} books...")
                time.sleep(1)  # polite delay

        df[['Availability', 'Search_URL', 'Final_URL']] = pd.DataFrame(results)

        st.success("✅ Search completed for all rows!")
        st.dataframe(df)

        # Download section
        csv_data = df.to_csv(index=False).encode('utf-8')
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Results')
        excel_data = excel_buffer.getvalue()

        st.download_button("⬇️ Download Results as CSV", data=csv_data, file_name='availability_results.csv', mime='text/csv')
        st.download_button("⬇️ Download Results as Excel", data=excel_data, file_name='availability_results.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.success("✅ Download your results!")
        st.balloons()