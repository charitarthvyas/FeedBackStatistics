# === Part 1: Import Necessary Libraries ===

# Import Streamlit. This is the main library for the web app.
import streamlit as st
# Import pandas for data manipulation (reading Excel, organizing data)
import pandas as pd
# Import altair for creating the interactive charts
import altair as alt
# We no longer need 'io' or 'google.colab' libraries

# === Part 2: Page Setup & Title ===

# Set the title and icon that will appear in the browser tab
st.set_page_config(
    page_title="Feedback Analysis Dashboard",
    page_icon="📊",
    layout="wide"
)

# Display the main title of the web app
st.title("📊 Student Feedback Analysis Dashboard")
st.write("Upload your feedback Excel file to automatically generate an interactive analysis chart.")

# === Part 3: File Upload ===

st.header("Step 1: Upload Your Feedback File")
# Create the file uploader widget. This is the Streamlit version of "files.upload()".
# It accepts Excel and CSV files.
uploaded_file = st.file_uploader("Choose an Excel or CSV file", type=["xlsx", "xls", "csv"])

# The entire rest of the app will only run IF a file has been uploaded.
if uploaded_file is not None:
    
    # Read the file into a pandas DataFrame
    # Streamlit's uploader object can be read directly by pandas.
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading the file: {e}")
        st.stop() # Stop the script if the file can't be read

    # Get the list of ALL column names from the uploaded file
    all_columns = df.columns.tolist()

    # === Part 4: Interactive Column Selector (Using a Form) ===
    
    # Using st.form() is the best practice.
    # It groups all the checkboxes and a "Submit" button.
    # This prevents the app from re-running every time a single box is checked.
    # The app will only re-run when the "Run Analysis" button is clicked.
    
    with st.form(key='column_selector_form'):
        st.header("Step 2: Select Feedback Questions")
        st.write("Check the boxes for all columns you want to analyze. The app will try to guess for you.")
        
        # We will store the state (True/False) of each checkbox in a dictionary
        checkbox_states = {}

        # Create a checkbox for every column in the file
        for col in all_columns:
            # We'll pre-check the box if the column name looks like a feedback question
            pre_check = 'Teacher-Specific Reflection' in col or '👉' in col
            
            # The st.checkbox() function creates a checkbox and returns its current state (True/False)
            checkbox_states[col] = st.checkbox(col, value=pre_check)

        # Create the "Submit" button for the form
        submitted = st.form_submit_button("Run Analysis on Selected Columns")

    # === Part 5: Analysis & Charting ===
    
    # This 'if submitted:' block will ONLY run after the user clicks the button.
    if submitted:
        
        # 1. Get the list of columns the user selected
        feedback_cols = [col for col, checked in checkbox_states.items() if checked]

        # 2. Check if the user selected any columns
        if not feedback_cols:
            st.error("Error: You must select at least one feedback column to analyze. Please check the boxes and try again.")
            st.stop() # Stop

        # 3. Show a "spinner" while the data is processing
        with st.spinner("Analyzing data and building your chart..."):
            
            # Get the total number of student responses
            total_responses = len(df)
            
            # 'Melt' the data (from wide to long) using ONLY the columns you selected
            df_long = df.melt(
                id_vars=[col for col in df.columns if col not in feedback_cols],
                value_vars=feedback_cols,
                var_name='Criterion',
                value_name='Response'
            )

            # --- IMPORTANT: Response Values ---
            # These values MUST be in your Excel file for the chart to work.
            response_to_category = {
                'Strongly Agree ✅': 'Strongly Agree',
                'Agree ✋🏻': 'Agree',
                'Disagree ⚠️': 'Disagree',
                'Strongly Disagree ⛔️': 'Strongly Disagree'
            }
            response_to_sentiment = {
                'Strongly Agree ✅': 'Positive',
                'Agree ✋🏻': 'Positive',
                'Disagree ⚠️': 'Negative',
                'Strongly Disagree ⛔️': 'Negative'
            }

            # Map the responses to categories and sentiments
            df_long['Response Category'] = df_long['Response'].map(response_to_category)
            df_long['Sentiment'] = df_long['Response'].map(response_to_sentiment)

            # Drop any rows where the response wasn't one of the 4 expected values
            df_long = df_long.dropna(subset=['Response Category', 'Sentiment'])

            # --- Percentage Calculation ---
            df_counts = df_long.groupby(['Criterion', 'Response Category', 'Sentiment']).size().reset_index(name='Count')
            df_totals = df_long.groupby('Criterion').size().reset_index(name='Total')
            df_perc = pd.merge(df_counts, df_totals, on='Criterion')
            df_perc['Percentage'] = df_perc['Count'] / df_perc['Total']

            # Create the Diverging Percentage (Negative values go left, Positive go right)
            df_perc['Diverging Percentage'] = df_perc.apply(
                lambda row: row['Percentage'] * -1 if row['Sentiment'] == 'Negative' else row['Percentage'],
                axis=1
            )

            # --- Dynamic Short Names ---
            # Automatically number and shorten the selected column names for the chart
            criterion_short_map = {
                col_name: f"{i+1}. {col_name[:60]}..." if len(col_name) > 60 else f"{i+1}. {col_name}" 
                for i, col_name in enumerate(feedback_cols)
            }
            
            df_perc['Criterion'] = df_perc['Criterion'].map(criterion_short_map)
            sorted_criteria = sorted(criterion_short_map.values())

            # === Create the Interactive Chart ===
            color_domain = ['Strongly Agree', 'Agree', 'Disagree', 'Strongly Disagree']
            color_range = ['#006837', '#31a354', '#fb6a4a', '#a50f15'] # Dk Green, Lt Green, Lt Red, Dk Red

            base = alt.Chart(df_perc).properties(
                title=f'Student Feedback Analysis (N={total_responses})'
            )

            bar = base.mark_bar().encode(
                x=alt.X('Diverging Percentage', stack='zero', axis=alt.Axis(format='%', title='Percentage of Responses', grid=True)),
                y=alt.Y('Criterion', sort=sorted_criteria, axis=alt.Axis(title=None)), # Use the new short, sorted names
                color=alt.Color('Response Category', scale=alt.Scale(domain=color_domain, range=color_range), legend=alt.Legend(title="Response")),
                order=alt.Order('Response Category', sort='descending'),
                tooltip=[
                    alt.Tooltip('Criterion', title='Question'),
                    'Response Category',
                    'Count',
                    alt.Tooltip('Percentage', format='.1%', title='Percent of Category')
                ]
            )
            
            # --- Display the Chart ---
            st.header("Step 3: Your Interactive Chart")
            st.success("Analysis complete! Hover over the chart for details.")
            
            # This is the Streamlit command to display an Altair chart
            st.altair_chart(bar, use_container_width=True)