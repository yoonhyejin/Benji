import smtplib, ssl
import psycopg2
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import calendar
from datetime import datetime
import codecs
import numpy as np


class BenjiReports:

    def  __init__(self):

        #### date-related ####
        self.today = datetime.today()
        self.year = int(datetime.strftime(self.today, "%Y"))
        self.month = int(datetime.strftime(self.today, "%m"))
        self.month_name = calendar.month_name[self.month]
        self.start_dte = self.today.replace(day=1)

        #### AWS SES ####
        self.sender_email = ""
        self.receiver_email = ""
        self.host = ''
        self.port = 465
        self.username_smtp = ''
        self.password_smtp = ''

        self.currency = 1000
        self.daily_threshold = 6
        self.overwork_bonus = 1.1

        print("INIT")

    def __enter__(self):
        self.conn = psycopg2.connect("host= dbname= user= password=") #postgresql connection information
        self.cur = self.conn.cursor()
        print("ENTER")

        self.get_weekdays()
        self.get_worked_days()
        self.get_early_days()
        self.get_total_hour()
        self.get_total_won()
        self.get_message()

        self.backup_data()
        self.send_email()

        return self.cur

    def backup_data(self): #backup this month's data
        backup_sql = """
                    INSERT INTO benji_backup (ctg, start_dte, end_dte, total_hour)
                    VALUES (%s, %s, %s, %s)
                    """
        self.cur.execute(backup_sql, ["m", self.start_dte, self.today, self.total_hour])
        self.conn.commit()

    def send_email(self):
        context = ssl.create_default_context()
        message = self.get_message()
        with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
            server.login(self.username_smtp, self.password_smtp)
            server.sendmail(self.sender_email, self.receiver_email, message.as_string())


    def get_weekdays(self):
        day_list =  [(self.year, self.month, d) for d in range(1, calendar.monthrange(self.year, self.month)[1] + 1)]
        day_list = [day for day in day_list if calendar.weekday(day[0],day[1],day[2]) not in [5,6]]
        self.weekdays = len(day_list)
        return self.weekdays


    def get_worked_days(self):
        sql = """
            WITH n AS
                (SELECT now() AT TIME ZONE 'ASIA/SEOUL' AS ts)
            SELECT count(DISTINCT dte) AS worked_d
            FROM benji,
                 n
            WHERE dte BETWEEN date_trunc('month', n.ts) AND n.ts::date
            """
        self.cur.execute(sql)
        self.worked_days = int(self.cur.fetchone()[0])
        return self.worked_days

    def get_early_days(self):
        sql = """
            WITH n AS
              (SELECT now() AT TIME ZONE 'ASIA/SEOUL' AS ts)
            SELECT count(DISTINCT a.dte) AS early_d
            FROM
              (SELECT dte,
                      min(in_ts) AS start_time
               FROM benji,
                    n
               WHERE dte BETWEEN date_trunc('month', n.ts) AND n.ts::date
               GROUP BY dte) AS a
            WHERE extract(HOUR
                          FROM start_time) < 9
            """
        self.cur.execute(sql)
        self.early_days = int(self.cur.fetchone()[0])
        self.early_perc = np.round(self.early_days/self.worked_days,2)*100
        return self.early_days, self.early_perc


    def get_total_hour(self):
        sql = """
            WITH n AS
            (
                   SELECT Now() at time zone 'Asia/Seoul' AS ts)
            SELECT   Sum(net_time)/60 +
                     CASE
                              WHEN Extract(epoch FROM max(out_ts) - max(in_ts)) < 0 OR max(out_ts) is null THEN (Extract(epoch FROM (n.ts - Max(in_ts))))/3600
                              ELSE 0
                     END AS monthly_time
            FROM     benji,
                     n
            WHERE    dte BETWEEN Date_trunc('month', n.ts) AND      n.ts::date
            GROUP BY n.ts
            """
        self.cur.execute(sql)
        self.total_hour = np.round(self.cur.fetchone()[0],2)
        return self.total_hour

    def get_total_won(self):
        overwork_bonus = 1
        self.monthly_threshold = self.weekdays * self.daily_threshold
        if self.total_hour >= self.monthly_threshold:
            overwork_bonus = self.overwork_bonus
        self.total_won= int((self.total_hour + self.early_days)*overwork_bonus*self.currency)
        return self.total_won


    def get_message(self):
        subject = "[BENJI] Your Monthly Report for {}, {}".format(self.year, self.month)

        body = """
        Hello, Sir.

        This is Benji - your personal time manager.
        How have you been this month so far?

        Here are some stats :

        * Your total working hour for this month : {} hours.
        * You worked {} days out of {} weekdays in {}.
        * You started your work before 9am {} days out of {} days your worked. ({}%)

        Since you charge {} won per hour & per 1 early day,
        you can flex {} won this month.

        You can view your detailed statistics in the link below.
        (my_link)
        Good luck next month.

        Best Regards,

        Benji """.format(self.total_hour,
                        self.worked_days, self.weekdays, self.month_name,
                        self.early_days, self.worked_days, self.early_perc,
                        self.currency, self.total_won)


        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = self.receiver_email
        message["Subject"] = subject
        message["Bcc"] = self.receiver_email  # Recommended for mass emails

        # Add body to email
        message.attach(MIMEText(body, "plain"))

        ### Send Gif
        if self.total_hour  >= self.monthly_threshold:
            gif_name = "img/willsmith.gif"
        else:
            gif_name = "img/youdidit.gif"

        f = codecs.open(gif_name, 'rb')
        attachment = MIMEImage(f.read())
        attachment.add_header('Content-Disposition', 'attachment', filename=gif_name)
        message.attach(attachment)
        return message

    def __exit__(self, exc_type, exc_value, exc_trace) -> None:
        self.cur.close()
        self.conn.close()
        print("EXIT")


if __name__ == '__main__':
    with BenjiReports() as B:
        print("Email Sent!")
