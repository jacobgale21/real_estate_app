import openai
import os
import dotenv
import pandas as pd
import re
dotenv.load_dotenv()

# Call chatgpt through an api
def generate_chatgpt_prompt_mini(property_info, price_info, feature_info):
    prompt = f"""
    You are a professional real estate market analyst specializing in MLS-based comparative market reports. 
    Your job is to create a detailed, appraisal-style report with comparing a subject property against multiple comparable sales. 
    Do not include any tables just include bullet points and a summary for each section. Each section should be named as the section title followed by a summary -
    Follow the exact structure below:
    1. Size & Price Positioning
    2. Notable Feature Comparisons 
    3. Market Context & Value Implications
    4. Appraisal Perspective
    5. Summary
    Include bullet points for observations. Be precise in calculations.\n\n"""
    for idx, row in property_info.iterrows():
        prompt += f"Property {idx + 1}:\n"
        for key, value in row.items():
            prompt += f"{key}: {value} | "
        for key, value in price_info.iloc[idx].items():
            if key != 'Address':
                prompt += f"{key}: {value} | "
        for key, value in feature_info.iloc[idx].items():
            if key != 'Address':
                prompt += f"{key}: {value} | "
        prompt += "\n\n"
    prompt += f"Please produce the full appraisal-style comparison for the subject property: {property_info['Address'].iloc[0]} versus the other {len(property_info) - 1} properties. Follow the section structure exactly."
    return prompt

def generate_chatgpt_prompt_features(features_info):
    prompt = f"""
    For each of the following properties, write a list of features that are important to the properties.
    Each different feature type should be delimited by a | character.  The feature types should be the same for each property. The feature types are treated as keys and the values are treated as values. The output should be structured the same way as the input property information.
    The feature types should be features that people would care about when buying a property. Do not include garage, bed/bath count information.
    """
    for idx, row in features_info.iterrows():
        prompt += f"Property {idx + 1}:\n"
        for key, value in row.items():
            prompt += f"{key}: {value} | "
        prompt += "\n\n"
    prompt += f"Please produce the list of features for the properties. Do not include any other text in your response."
    return prompt

# Calling chatgpt for feature comparisons
def get_feature_list(prompt):
    # openai.api_key = os.getenv("OPENAI_API_KEY")
    # response = openai.ChatCompletion.create(
    #     model="gpt-5",
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # chatgpt_message = response.choices[0].message.content["content"]
    # print("Chatgpt message: ", chatgpt_message)
    chatgpt_message = prompt
    
    # Split by property sections
    property_sections = chatgpt_message.split("Property")
    property_sections = [section.strip() for section in property_sections if section.strip()]
    
    feature_df = pd.DataFrame()
    
    for section in property_sections:
        # Skip if it's just a number (like "1:")
        if section.startswith(('1:', '2:', '3:', '4:', '5:')):
            section = section[2:].strip()  # Remove the number and colon
        
        # Split the section by pipe to get individual features
        features = section.split("|")
        features = [feature.strip() for feature in features if feature.strip()]
        
        # Create a dictionary for this property
        property_dict = {}
        
        for feature in features:
            parts = feature.split(":", 1)
            if len(parts) > 1:
                key = parts[0].strip()
                value = parts[1].strip()
                property_dict[key] = value
        
        # Add to dataframe if we have data
        if property_dict:
            property_df = pd.DataFrame([property_dict])
            feature_df = pd.concat([feature_df, property_df], axis=0, ignore_index=True)
    
    return feature_df
    

# Parse ChatGPT report into per-section DataFrames
def parse_report_sections(chatgpt_message: str) -> dict:
    """
    Parse a report formatted with sections like:
    "Size & Price Positioning — summary: ...\n<bullets>\n ..."
    Returns: dict[str, pandas.DataFrame]
      - key: section title
      - value: DataFrame with columns [title, item_type, text, order, summary]
        where item_type in {"summary","bullet"}
    """
    

    section_titles = [
        "Size & Price Positioning",
        "Notable Feature Comparisons",
        "Market Context & Value Implications",
        "Appraisal Perspective",
        "Summary",
    ]

    # Build a regex that matches any title followed by dash/em-dash and "summary:"
    title_regex = r"|".join(re.escape(t) for t in section_titles)
    header_pattern = re.compile(
        rf"^(?P<title>{title_regex})\s*[—-]\s*summary:\s*(?P<summary>.*)$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Find all headers and their spans
    headers = list(header_pattern.finditer(chatgpt_message))
    sections: dict[str, pd.DataFrame] = {}

    for i, match in enumerate(headers):
        title = match.group("title").strip()
        summary = match.group("summary").strip()
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(chatgpt_message)
        block = chatgpt_message[start:end].strip()

        # Split block into lines; treat each non-empty line as a bullet
        raw_lines = [ln.strip() for ln in block.splitlines()]
        bullets: list[str] = []
        # Join wrapped lines: if a line does not end with sentence punctuation, append the next
        buffer = ""
        for ln in raw_lines:
            if not ln:
                continue
            if buffer:
                buffer = f"{buffer} {ln}".strip()
            else:
                buffer = ln
            if buffer.endswith(('.', '!', '?', '”', '"')):
                bullets.append(buffer)
                buffer = ""
        if buffer:
            bullets.append(buffer)

        rows = []
        # Summary row
        rows.append({
            "title": title,
            "item_type": "summary",
            "text": summary,
            "order": 0,
            "summary": summary,
        })
        # Bullet rows
        for idx, b in enumerate(bullets, start=1):
            rows.append({
                "title": title,
                "item_type": "bullet",
                "text": b,
                "order": idx,
                "summary": summary,
            })

        sections[title] = pd.DataFrame(rows)

    return sections

# Calling chatgpt mini with prompt
def call_chatgpt_mini(prompt):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    chatgpt_message = response.choices[0].message.content["content"]
    # Parse sections (result available for callers that import this module)
    try:
        _ = parse_report_sections(chatgpt_message)
    except Exception:
        pass
    return chatgpt_message

# Main function that will be called when the api is called in the backend
def get_chatgpt_response(property_info, price_info, feature_info):
# Calling chatgpt mini for main response
    feature_prompt = generate_chatgpt_prompt_features(feature_info)
    # Will be a dataframe with the features
    feature_df = get_feature_list(feature_prompt)
    # Get the overall prompt
    mini_prompt = generate_chatgpt_prompt_mini(property_info, price_info, feature_df)
    
    chat_response = call_chatgpt_mini(mini_prompt)
    # Call chatgpt
    return chat_response