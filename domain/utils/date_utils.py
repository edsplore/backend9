from datetime import datetime

from utils.logger import Logger  # Ensure correct import path for your project
logger = Logger.get_logger(__name__)
class DateUtils:
    def __init__(self):
        logger.info("DateUtils initialized.")
    
    def get_current_date(self):
        return datetime.now().strftime("%Y-%m-%d")
    
    def convert_to_human_readable(self, date_str: str):
        try:
            logger.info("Converting date to human readable format.")
            logger.debug(f"date_str={date_str}")
            # Parse the ISO 8601 date string
            date_time = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        
            # List of months with long names to be abbreviated
            short_month_names = {
                "January": "Jan",
                "February": "Feb",
                "March": "Mar",
                "April": "Apr",
                "May": "May",
                "June": "Jun",
                "July": "Jul",
                "August": "Aug",
                "September": "Sep",
                "October": "Oct",
                "November": "Nov",
                "December": "Dec"
            }
            
            # Get the full month name
            full_month_name = date_time.strftime("%B")
            
            # Use abbreviated form if it's in long_months
            month = short_month_names.get(full_month_name, full_month_name)
            
            # Format as "D Month YYYY"
            return f"{date_time.day} {month} {date_time.year}"
        except Exception as e:
            logger.error(f"Error converting date to human readable format: {str(e)}", exc_info=True)
            return date_str