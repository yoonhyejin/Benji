import psycopg2
from datetime import datetime, timedelta
import numpy as np


class BenjiWeeklyBackup:

    def  __init__(self):

        #### date-related ####
        self.today = datetime.today()
        self.start_dte = self.today - timedelta(days=self.today.weekday()) #this monday

        print("INIT")

    def __enter__(self):
        self.conn = psycopg2.connect("host= dbname= user= password=") #postgresql connection information
        self.cur = self.conn.cursor()
        print("ENTER")

        self.get_total_hour()
        self.backup_data()

        return self.cur

    def backup_data(self): #back up this month's data
        backup_sql = """
                    INSERT INTO benji_backup (ctg, start_dte, end_dte, total_hour)
                    VALUES (%s, %s, %s, %s)"""
        self.cur.execute(backup_sql, ["w", self.start_dte, self.today, self.total_hour])
        self.conn.commit()


    def get_total_hour(self): #get this week's total working hour
        sql = """
            WITH n AS
            (
                   SELECT Now() at time zone 'Asia/Seoul' AS ts)
            SELECT   Sum(net_time)/60 +
                     CASE
                              WHEN Extract(epoch FROM Max(out_ts) - Max(in_ts)) < 0 OR max(out_ts) is null THEN (Extract(epoch FROM (n.ts - Max(in_ts))))/3600
                              ELSE 0
                     END AS weekly_time
            FROM     benji,
                     n
            WHERE    dte BETWEEN Date_trunc('week', n.ts) AND      n.ts::date
            GROUP BY n.ts
            """
        self.cur.execute(sql)
        self.total_hour = np.round(self.cur.fetchone()[0],2)
        return self.total_hour



    def __exit__(self, exc_type, exc_value, exc_trace) -> None:
        self.cur.close()
        self.conn.close()
        print("EXIT")


if __name__ == '__main__':
    with BenjiWeeklyBackup() as B:
        print("Weekly data backed up.")
