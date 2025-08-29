import openai
import os
import dotenv
import pandas as pd
dotenv.load_dotenv()

# Call chatgpt through an api
def generate_chatgpt_prompt_mini(property_info, price_info, feature_info):
    prompt = f"""
    You are a professional real estate market analyst specializing in MLS-based comparative market reports. 
    Your job is to create a detailed, appraisal-style report with comparing a subject property against multiple comparable sales. 
    Do not include any tables just include a summary and bullet points for each section.
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
    Each different feature type should be delimited by a | character. The feature types should be the same for each property.
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
    # Convert to dataframe
    feature_list = chatgpt_message.split("|")
    feature_list = [feature.strip() for feature in feature_list]
    # Loop through the first property
    feature_df = pd.DataFrame()
    curr_feature_df = pd.DataFrame()
    for feature in feature_list:
        parts = feature.split(":", 1)
        if len(parts) > 1:
            key = parts[0].strip()
            value = parts[1].strip()
            # If a new property starts, flush the previous one
            if key == "Address" and not curr_feature_df.empty and curr_feature_df.notna().any(axis=None):
                feature_df = pd.concat([feature_df, curr_feature_df], axis=0, ignore_index=True)
                curr_feature_df = pd.DataFrame(index=[0])
            curr_feature_df.loc[0, key] = value
    # flush the last one
    if not curr_feature_df.empty and curr_feature_df.notna().any(axis=None):
        feature_df = pd.concat([feature_df, curr_feature_df], axis=0, ignore_index=True)

    return feature_df
    

# Calling chatgpt mini with prompt
def call_chatgpt_mini(prompt):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    chatgpt_message = response.choices[0].message.content["content"]
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