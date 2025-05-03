import os
import pandas as pd
from faker import Faker
import random

# Set up
os.makedirs("../data/raw", exist_ok=True)
fake = Faker()
Faker.seed(0)

# Generate 100 rows of fake data
data = pd.DataFrame({
    "id": [i + 1 for i in range(100)],
    "name": [fake.first_name() for _ in range(100)],
    "value": [random.randint(10, 1000) for _ in range(100)]
})

# Save to CSV
data.to_csv("../data/raw/example_data.csv", index=False)
print("[extract] example_data.csv created with 100 fake rows.")
