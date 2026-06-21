# src/seed_auradb.py
import os
import time
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load credentials from root .env
load_dotenv()

class AuraDBSync:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        
        print(f"[*] Connecting securely to cloud instance: {uri}")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

    def populate_database(self, accounts_path, transactions_path):
        start_time = time.time()
        
        # Load your existing datasets
        print("[-] Loading raw dataset files...")
        df_accounts = pd.read_csv(accounts_path)
        df_tx = pd.read_csv(transactions_path)

        # Standardize missing/empty values
        df_accounts['name'] = df_accounts['name'].fillna("Unknown Entity")
        if 'bank' not in df_accounts.columns and 'institution' in df_accounts.columns:
            df_accounts['bank'] = df_accounts['institution']
        df_accounts['bank'] = df_accounts['bank'].fillna("KYC Pending")
        df_tx['Payment_currency'] = df_tx['Payment_currency'].fillna("NPR")
        df_tx['cross_border_flag'] = df_tx['cross_border_flag'].fillna(0).astype(int)

        with self.driver.session() as session:
            # 1. Purge remote database
            print("[-] Purging existing database entries...")
            session.run("MATCH (n) DETACH DELETE n")

            # 2. Write Account Nodes
            print("[-] Writing Account nodes to AuraDB...")
            accounts_list = df_accounts.to_dict('records')
            session.run("""
                UNWIND $rows AS row
                CREATE (a:Account {
                    id: toString(row.account_id),
                    name: row.name,
                    bank: row.bank,
                    risk_score: toFloat(0.0)
                })
            """, rows=accounts_list)

            # 3. Create Constraints & Indexes
            print("[-] Generating constraints...")
            session.run("CREATE CONSTRAINT UNIQUE_ACC_ID IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE")

            # 4. Batch Transaction Relationships
            print("[-] Writing SENDS transactional edges in batches...")
            transactions_list = df_tx.to_dict('records')
            batch_size = 5000
            total_records = len(transactions_list)

            for i in range(0, total_records, batch_size):
                batch = transactions_list[i:i + batch_size]
                session.run("""
                    UNWIND $rows AS row
                    MATCH (from:Account {id: toString(row.Sender_account)})
                    MATCH (to:Account {id: toString(row.Receiver_account)})
                    CREATE (from)-[:SENDS {
                        amount: toFloat(row.amount_local_npr),
                        date: row.Date,
                        time: row.Time,
                        currency: row.Payment_currency,
                        cross_border: toInteger(row.cross_border_flag)
                    }]->(to)
                """, rows=batch)
                print(f"    - Uploaded Batch {i//batch_size + 1}: Records {i} to {min(i+batch_size, total_records)}")

        duration = time.time() - start_time
        print(f"[+] AuraDB seeding complete: {duration:.2f} seconds.")

if __name__ == "__main__":
    seeder = AuraDBSync()
    seeder.populate_database(
        "data/STUDENT_DATASET/accounts.csv",
        "data/STUDENT_DATASET/transactions.csv"
    )
    seeder.close()
