"""
This module provides functions for adding blockchain data and technical indicators to a DataFrame.

Functions:
- add_blockchain_data: Fetches data from specified blockchain.com API endpoints and adds it to the DataFrame.
- add_all_technical_indicators: Adds technical indicators to the data.

This module uses pandas for data manipulation and several functions from the src.features.blockchain and src.features.ta modules 
to fetch blockchain data and calculate technical indicators.
"""

import pandas as pd

from src.features.blockchain import (
    get_hash_rate_over_time,
    get_avg_block_size,
    get_network_difficulty,
    get_miners_revenue,
    get_mempool_size,
)

from src.features.ta import (
    calculate_bollinger_bands,
    calculate_stochastic_oscillator,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_ema,
    calculate_atr,
    calculate_macd_histogram,
    calculate_obv,
    calculate_cci,
)

from src.features.extraction.lstm import (
    create_sequences,
    build_lstm_model,
    train_model,
)

from src.data.data_cleaning import clean_data


def add_blockchain_data(data, timespan="1year", start=None):
    """
    Fetches data from specified blockchain.com API endpoints and adds it to the DataFrame.

    :param data: A Pandas DataFrame with the price data.
    :param timespan: The timespan for the blockchain data (e.g., '1year' for 1 year).
    :param start: The start date for the data in YYYY-MM-DD format.
    :return: The DataFrame with the added blockchain data.
    """
    # Fetch the hash rate over time
    hash_rate_data = get_hash_rate_over_time(timespan, start_date=start)

    # Fetch the average block size over time
    avg_block_size_data = get_avg_block_size(timespan, start_date=start)

    # Fetch the network difficulty over time
    network_difficulty_data = get_network_difficulty(timespan, start_date=start)

    # Fetch the miners revenue over time
    miners_revenue_data = get_miners_revenue(timespan, start_date=start)

    # Fetch the mempool size over time
    mempool_size_data = get_mempool_size(timespan, start_date=start)

    # Convert the dates in the 'data' DataFrame to the same format as the dates in the 'hash_rate_df' DataFrame
    data.index = data.index.date

    # Merge the fetched data with the main DataFrame
    data = pd.merge(data, hash_rate_data, how="left", left_index=True, right_index=True)
    data = pd.merge(
        data, avg_block_size_data, how="left", left_index=True, right_index=True
    )
    data = pd.merge(
        data, network_difficulty_data, how="left", left_index=True, right_index=True
    )
    data = pd.merge(
        data, miners_revenue_data, how="left", left_index=True, right_index=True
    )

    # Resample to daily frequency
    mempool_size_data = mempool_size_data.resample("D").mean()

    # Then merge
    data = pd.merge(
        data, mempool_size_data, how="left", left_index=True, right_index=True
    )

    # Clean the data
    data = clean_data(data)

    return data


def add_all_technical_indicators(data):
    """
    Add all technical indicators to the data.

    :param data: A Pandas DataFrame with the price data.
    :return: The DataFrame with the added technical indicators. Rows containing NaN values
             due to the calculation of technical indicators are dropped.
    """
    # add the indicators
    data["upper_bb"], data["middle_bb"], data["lower_bb"] = calculate_bollinger_bands(
        data["Close"]
    )
    data["slowk"], data["slowd"] = calculate_stochastic_oscillator(data)
    data["macd"], data["macdsignal"], data["macdhist"] = calculate_macd(data["Close"])
    data["rsi"] = calculate_rsi(data["Close"])
    data["sma"] = calculate_sma(data["Close"])
    data["ema"] = calculate_ema(data["Close"])
    data["atr"] = calculate_atr(data)
    data["macd_hist"] = calculate_macd_histogram(data["Close"])
    data["obv"] = calculate_obv(data)
    data["cci"] = calculate_cci(data)

    # Reclean the data
    data = clean_data(data)

    return data


def extract_lstm_features(df, sequence_length):
    """
    Extracts features from the data using an LSTM model.

    :param df: A Pandas DataFrame with the processed data.
    :param sequence_length: The length of the sequences to be created from the data.
    :return: A DataFrame with the extracted features.
    """
    # Create sequences from the DataFrame
    X = create_sequences(df, sequence_length)

    # Build an LSTM model
    model = build_lstm_model(input_shape=(sequence_length, df.shape[1]))

    # Train the LSTM model as an autoencoder (reconstructing its input)
    model = train_model(model, X, epochs=10)

    # Extract features from the LSTM model
    # This could be the outputs of the LSTM layer, for example
    features = model.predict(X)

    # Calculate the mean of the LSTM outputs for each sequence
    features_mean = features.mean(axis=(1, 2))

    # Convert the extracted features to a DataFrame
    features_df = pd.DataFrame(features_mean, columns=["lstm_feature"])

    # Adjust the index of the features DataFrame to match the original DataFrame
    features_df.index = df.index[sequence_length - 1 : -1]

    # Add the extracted features to the original DataFrame
    df = pd.concat([df, features_df], axis=1)

    return df
