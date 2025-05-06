from typing import List
from datetime import datetime
from domain.services.assignment_service import AssignmentService
from api.schemas.responses import (FetchAssignedPlansResponse, Stats,
                                   StatsData,
                                   AdminDashboardUserActivityStatsResponse, AdminDashboardUserActivityResponse,AdminDashboardUserActivityStatsResponse, AdminDashboardUserActivityStatsUserType,
                                   CreateUserResponse)
from infrastructure.database import Database
from fastapi import HTTPException
from domain.utils.date_utils import DateUtils
import math

from utils.logger import Logger  # Ensure correct import path for your project

logger = Logger.get_logger(__name__)


class UserService:

    def __init__(self):
        self.db = Database()
        logger.info("UserService initialized.")

    async def get_user_assignments_with_stats(self, user_id: str):
        logger.info("Fetching user assignments with stats.")
        logger.debug(f"user_id={user_id}")
        assignment_service = AssignmentService()
        try:
            assignments_with_stats: FetchAssignedPlansResponse = await assignment_service.fetch_assigned_plans(
                user_id)
            logger.info(f"Fetched assignments for user_id={user_id}.")
            return assignments_with_stats
        except Exception as e:
            logger.error(
                f"Error fetching assignments for user_id={user_id}: {str(e)}",
                exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=
                f"Error fetching assignments for user_id={user_id}: {str(e)}")

    async def get_admin_dashboard_user_activity(
            self,
            user_id: str) -> List[AdminDashboardUserActivityResponse]:
        logger.info("Fetching all users total simulations.")

        
        users = await self.db.users.find({}).to_list(None)

        userData = []

        core_user_list = [
                            {
                            "user_id": "67ab1c82c064790d63817fd8",
                            "first_name": "Nubrux",
                            "last_name": "Franni",
                            "email": "nubruxoufranni-5775@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI BPO",
                            "department": "BPO Services",
                            "reporting_to": {
                                "id": "679a0c65346f3e2dedaa9739",
                                "name": "Charlie White"
                            },
                            "hiring_date": "2024-12-18",
                            "class_id": "DFR195",
                            "internal_user_id": "decora",
                            "external_user_id": "nubrux",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-11T09:46:42.325Z"
                            },
                            "updated": {
                                "user": {
                                "id": "null",
                                "name": "Abhinav Pandey"
                                },
                                "time": "2025-02-17T05:33:28.794Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "6799e1ce346f3e2dedaa970e",
                                "name": "SUPERVISOR",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67a4885a9cfbfa3a4a14eb45",
                            "first_name": "Test",
                            "last_name": "Dev2",
                            "email": "testdev2@mail.com",
                            "phone_no": "",
                            "division": "newDivision",
                            "department": "newDept",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-06T10:00:58.12Z"
                            },
                            "updated": {
                                "user": {
                                "id": "null",
                                "name": "Abhinav Pandey"
                                },
                                "time": "2025-02-17T05:33:28.794Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67b41a9357c4ea240c699092",
                            "first_name": "Souvik",
                            "last_name": "Santra",
                            "email": "ssantra@c3connect.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Engineering Dev",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "null",
                                "name": "New User"
                                },
                                "time": "2025-02-18T05:28:51.104Z"
                            },
                            "updated": {
                                "user": {
                                "id": "null",
                                "name": "New User"
                                },
                                "time": "2025-02-18T05:28:51.105Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ce346f3e2dedaa970e",
                                "name": "SUPERVISOR",
                                "product": "Guidance"
                                },
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67ac8d1896dee9352f1ee589",
                            "first_name": "Anmol",
                            "last_name": "Goel",
                            "email": "agoel@c3connect.com",
                            "phone_no": "+919876543210",
                            "division": "EverAI Product",
                            "department": "Engineering Dev",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "null",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-12T11:59:20.841Z"
                            },
                            "updated": {
                                "user": {
                                "id": "null",
                                "name": "New User"
                                },
                                "time": "2025-02-18T08:10:14.892Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "6799e1b2346f3e2dedaa970d",
                                "name": "agent",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67e24b9568a2890d25686d54",
                            "first_name": "Tredder",
                            "last_name": "Madau",
                            "email": "treddegremmadau-4178@yopmail.com",
                            "phone_no": "",
                            "division": "IT",
                            "department": "Product Design dev",
                            "reporting_to": {
                                "id": "67b8104a924ba33c9cf531f1",
                                "name": "Robert Brown"
                            },
                            "hiring_date": "2025-03-12",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-03-25T06:22:13.125Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-03-25T06:22:13.125Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67e2a7ed15988a0adb9ddf30",
                            "first_name": "new",
                            "last_name": "user",
                            "email": "todaynewuser@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Product Design VD",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-03-25T12:56:13.914Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-03-25T12:56:13.914Z"
                            },
                            "roles": [
                                {
                                "role_id": "67c042b1e85b6771b0d14a78",
                                "name": "TRAINEE",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67b80fdf924ba33c9cf531ef",
                            "first_name": "Emilia",
                            "last_name": "Clark",
                            "email": "emily.clark@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI BPO",
                            "department": "BPO Services",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-02-21T05:32:15.821Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-02-21T10:42:16.477Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e174346f3e2dedaa970b",
                                "name": "Manager",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67dcf4082659f430cbede906",
                            "first_name": "FirstName99",
                            "last_name": "LastName99",
                            "email": "user99@yopmail.com",
                            "phone_no": "+61412345678",
                            "division": "IT",
                            "department": "Payroll",
                            "reporting_to": {
                                "id": "67dd3e458b780e75388959c0",
                                "name": "FirstName437 LastName437"
                            },
                            "hiring_date": "2009-10-29",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-03-21T05:07:20.015Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-03-21T05:07:20.015Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ce346f3e2dedaa970e",
                                "name": "SUPERVISOR",
                                "product": "Guidance"
                                },
                                {
                                "role_id": "6799e1fe346f3e2dedaa9710",
                                "name": "tester-1",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67dcf4082659f430cbede907",
                            "first_name": "FirstName100",
                            "last_name": "LastName100",
                            "email": "user100@yopmail.com",
                            "phone_no": "+91 9876543290",
                            "division": "IT",
                            "department": "Payroll",
                            "reporting_to": {
                                "id": "67da7678793af247df1e1745",
                                "name": "John Brown"
                            },
                            "hiring_date": "2019-07-19",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-03-21T05:07:20.015Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-03-21T05:07:20.015Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "6799e1b2346f3e2dedaa970d",
                                "name": "agent",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67a1188276d6606ab2c082b7",
                            "first_name": "Maneesh",
                            "last_name": "Singh",
                            "email": "msingh1@c3connect.com",
                            "phone_no": "+919199564523",
                            "division": "EverAI",
                            "department": "IT",
                            "reporting_to": {
                                "id": "67a5cf569cfbfa3a4a14eb4d",
                                "name": "Shivangi Agarwal"
                            },
                            "hiring_date": "2025-04-23",
                            "class_id": "string",
                            "internal_user_id": "msingh1",
                            "external_user_id": "msingh1",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "679a0c3f346f3e2dedaa9738",
                                "name": "Abhinav Pandey"
                                },
                                "time": "2025-02-03T19:26:58.102Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-05-05T08:56:42.634Z"
                            },
                            "roles": [
                                {
                                "role_id": "67ebe5b4b38db47a3d74253e",
                                "name": "Sim Creator",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67ebe7aab38db47a3d742547",
                            "first_name": "Simulator",
                            "last_name": "Creator",
                            "email": "simcreator@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Engineering Dev",
                            "reporting_to": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                            },
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-01T13:18:34.278Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-30T05:38:59.851Z"
                            },
                            "roles": [
                                {
                                "role_id": "67ebe5b4b38db47a3d74253e",
                                "name": "Sim Creator",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67a5cf569cfbfa3a4a14eb4d",
                            "first_name": "Test1",
                            "last_name": "Test11",
                            "email": "shivangi.agarwal@weareeverise.com",
                            "phone_no": "+917447422664",
                            "division": "Test",
                            "department": "Test",
                            "reporting_to": {
                                "id": "6818592ff629401dcd556be8",
                                "name": "Senthil Singh"
                            },
                            "hiring_date": "2029-10-10",
                            "class_id": "CLS_001",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-11T10:08:48.186Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-02-21T05:35:26.987Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ce346f3e2dedaa970e",
                                "name": "SUPERVISOR",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67da7678793af247df1e1745",
                            "first_name": "John",
                            "last_name": "Brown",
                            "email": "emily.johnson@yopmail.com",
                            "phone_no": "+917557322887",
                            "division": "Operations",
                            "department": "Development",
                            "reporting_to": {
                                "id": "67da7678793af247df1e1745",
                                "name": "John Brown"
                            },
                            "hiring_date": "2021-05-10",
                            "class_id": "CLS005",
                            "internal_user_id": "INT2",
                            "external_user_id": "EXT2",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-03-19T13:20:15.329Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-03-19T13:20:15.329Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "6799e1b2346f3e2dedaa970d",
                                "name": "agent",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67f6286b75b9226a9afabfaa",
                            "first_name": "Anmol",
                            "last_name": "Rishi",
                            "email": "anmol_test@yopmail.com",
                            "phone_no": "+919654115965",
                            "division": "EverAI Labs",
                            "department": "Product Design dev",
                            "reporting_to": {
                                "id": "67ebe72cb38db47a3d742543",
                                "name": "Simulator Manager"
                            },
                            "class_id": "",
                            "internal_user_id": "Anmol_internal",
                            "external_user_id": "Anmol_external",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-09T07:57:31.444Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-15T10:28:04.537Z"
                            },
                            "roles": [
                                {
                                "role_id": "67f6283975b9226a9afabfa9",
                                "name": "anmol_test",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67e3d4e3ba782a7d9721b43c",
                            "first_name": "new",
                            "last_name": "user",
                            "email": "newtestusershivi@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "IT",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-26T10:20:19.774Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-14T07:06:56.641Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e174346f3e2dedaa970b",
                                "name": "Manager",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67d932234e47293787466352",
                            "first_name": "Guru1",
                            "last_name": "Gurul1",
                            "email": "trafrigitribri-1@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "NewDpt1",
                            "reporting_to": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                            },
                            "hiring_date": "2024-01-02",
                            "class_id": "cid",
                            "internal_user_id": "idd1",
                            "external_user_id": "ext1",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-19T04:55:30.214Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1fe346f3e2dedaa9710",
                                "name": "tester-1",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "67c042b1e85b6771b0d14a78",
                                "name": "TRAINEE",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67ab888d68888e4d703fe8a4",
                            "first_name": "Test",
                            "last_name": "Test",
                            "email": "shivitest004@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Product Design dev",
                            "class_id": "test_123",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-11T17:27:41.6Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-02-27T14:08:33.498Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e174346f3e2dedaa970b",
                                "name": "Manager",
                                "product": "Guidance"
                                },
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67ac2c7349152a762c85d345",
                            "first_name": "Test",
                            "last_name": "Test",
                            "email": "Shivangi.Agarwal@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Product Design VD",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-12T05:06:59.904Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-21T12:44:49.952Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67ac932696dee9352f1ee58b",
                            "first_name": "Abhay",
                            "last_name": "Singh",
                            "email": "dummy@c3connect.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Product Design dev",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "null",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-12T12:25:10.074Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-21T12:45:54.697Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67b47e8590423f138a04232a",
                            "first_name": "Shivangi",
                            "last_name": "Agarwal",
                            "email": "sagarwal3@c3connect.com",
                            "phone_no": "+919876543800",
                            "division": "Development",
                            "department": "Hardware",
                            "reporting_to": {
                                "id": "67b81cbf47c7d3156535432f",
                                "name": "Jim Perry"
                            },
                            "hiring_date": "2025-02-08",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-02-18T12:35:17.009Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-04-21T05:22:58.336Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e174346f3e2dedaa970b",
                                "name": "Manager",
                                "product": "Guidance"
                                },
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                },
                                {
                                "role_id": "67ebe498b38db47a3d74253d",
                                "name": "Trainee",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "67f8ed77cc8d5324048d3ac8",
                                "name": "MANAGER",
                                "product": "QA & Coaching"
                                },
                                {
                                "role_id": "67f8eda5cc8d5324048d3ac9",
                                "name": "Manager",
                                "product": "VoiceBOT"
                                }
                            ]
                            },
                            {
                            "user_id": "67b8104a924ba33c9cf531f1",
                            "first_name": "Robert",
                            "last_name": "Brown",
                            "email": "robert.brown@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Product",
                            "department": "Product Design VD",
                            "class_id": "CLS_001",
                            "internal_user_id": "",
                            "external_user_id": "EXT#890",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-02-21T05:34:02.652Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-06T06:23:14.689Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ce346f3e2dedaa970e",
                                "name": "SUPERVISOR",
                                "product": "Guidance"
                                },
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                },
                                {
                                "role_id": "6799e1fe346f3e2dedaa9710",
                                "name": "tester-1",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67a483739cfbfa3a4a14eb39",
                            "first_name": "Staging",
                            "last_name": "Test",
                            "email": "stagingtest@gmail.com",
                            "phone_no": "+913242353323",
                            "division": "EverAI Labs",
                            "department": "Product Design dev",
                            "reporting_to": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                            },
                            "hiring_date": "2025-02-18",
                            "class_id": "uhaisu",
                            "internal_user_id": "masdsf",
                            "external_user_id": "EXT#890EXT#890",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-06T09:40:03.689Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-21T12:45:37.949Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e174346f3e2dedaa970b",
                                "name": "Manager",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67d932234e47293787466353",
                            "first_name": "Guru2",
                            "last_name": "Gurul2",
                            "email": "trafrigitribri-2@yopmail.com",
                            "phone_no": "",
                            "division": "NewD2",
                            "department": "NewDpt2",
                            "reporting_to": {
                                "id": "67c94a19262d4d7fd26ffeaf",
                                "name": "Test Test"
                            },
                            "hiring_date": "2024-01-03",
                            "class_id": "cid",
                            "internal_user_id": "idd2",
                            "external_user_id": "ext2",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "67c042b1e85b6771b0d14a78",
                                "name": "TRAINEE",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67d932234e47293787466356",
                            "first_name": "Guru5",
                            "last_name": "Gurul5",
                            "email": "trafrigitribri-5@yopmail.com",
                            "phone_no": "",
                            "division": "NewD5",
                            "department": "NewDpt5",
                            "reporting_to": {
                                "id": "67c94a19262d4d7fd26ffeaf",
                                "name": "Test Test"
                            },
                            "hiring_date": "2024-01-06",
                            "class_id": "cid",
                            "internal_user_id": "idd5",
                            "external_user_id": "ext5",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "67c042b1e85b6771b0d14a78",
                                "name": "TRAINEE",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67c94a19262d4d7fd26ffeaf",
                            "first_name": "Test",
                            "last_name": "Test",
                            "email": "tester1122@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Product Design dev",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-06T07:09:13.618Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-06T07:09:13.618Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67c00db0e85b6771b0d14a6f",
                            "first_name": "Raj",
                            "last_name": "Jakhmola",
                            "email": "rjakhmola@c3connect.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Engineering Dev",
                            "reporting_to": {
                                "id": "67a5cf569cfbfa3a4a14eb4d",
                                "name": "Shivangi Agarwal"
                            },
                            "class_id": "test_123",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-02-27T07:01:04.085Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-02-27T12:51:15.743Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "6799e1ce346f3e2dedaa970e",
                                "name": "SUPERVISOR",
                                "product": "Guidance"
                                },
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67d957a84e4729378746635e",
                            "first_name": "Emily",
                            "last_name": "Davis",
                            "email": "emily.davis76@yopmail.com",
                            "phone_no": "",
                            "division": "Test",
                            "department": "Test",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T11:23:20.905Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T11:23:20.905Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67c050b6e85b6771b0d14a7a",
                            "first_name": "Ellie",
                            "last_name": "Goulding",
                            "email": "elle.goulding123@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Product",
                            "department": "BPO Services",
                            "reporting_to": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                            },
                            "class_id": "CLS_010",
                            "internal_user_id": "INT-123",
                            "external_user_id": "EXT#890",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-02-27T11:47:02.909Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-02-27T11:53:38.209Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                },
                                {
                                "role_id": "67c042b1e85b6771b0d14a78",
                                "name": "TRAINEE",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67e3d7dc96c05e460c49c043",
                            "first_name": "new",
                            "last_name": "test",
                            "email": "newtestshivi11@yopmail.com",
                            "phone_no": "+35521243354",
                            "division": "Test",
                            "department": "Test",
                            "reporting_to": {
                                "id": "67ebe7aab38db47a3d742547",
                                "name": "Simulator Creator"
                            },
                            "hiring_date": "2025-01-16",
                            "class_id": "CLS_010",
                            "internal_user_id": "INT_010",
                            "external_user_id": "EXT_010",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-26T10:33:00.137Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-04-16T05:45:58.434Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1ee346f3e2dedaa970f",
                                "name": "superVISOR",
                                "product": "Knowledge Miner"
                                }
                            ]
                            },
                            {
                            "user_id": "67d932234e47293787466354",
                            "first_name": "Guru3",
                            "last_name": "Gurul3",
                            "email": "trafrigitribri-3@yopmail.com",
                            "phone_no": "",
                            "division": "NewD3",
                            "department": "NewDpt3",
                            "reporting_to": {
                                "id": "67c94a19262d4d7fd26ffeaf",
                                "name": "Test Test"
                            },
                            "hiring_date": "2024-01-04",
                            "class_id": "cid",
                            "internal_user_id": "idd3",
                            "external_user_id": "ext3",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "67c042b1e85b6771b0d14a78",
                                "name": "TRAINEE",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "67d932234e47293787466355",
                            "first_name": "Guru4",
                            "last_name": "Gurul4",
                            "email": "trafrigitribri-4@yopmail.com",
                            "phone_no": "",
                            "division": "NewD4",
                            "department": "NewDpt4",
                            "reporting_to": {
                                "id": "67c94a19262d4d7fd26ffeaf",
                                "name": "Test Test"
                            },
                            "hiring_date": "2024-01-05",
                            "class_id": "cid",
                            "internal_user_id": "idd4",
                            "external_user_id": "ext4",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-18T08:43:15.234Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e188346f3e2dedaa970c",
                                "name": "agent",
                                "product": "Simulator"
                                },
                                {
                                "role_id": "67c042b1e85b6771b0d14a78",
                                "name": "TRAINEE",
                                "product": "Guidance"
                                }
                            ]
                            },
                            {
                            "user_id": "680a651d2e304b725c43af32",
                            "first_name": "sunita",
                            "last_name": "Giri",
                            "email": "sgiri@c3connect.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "IT",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-04-24T16:21:49.954Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-04-24T16:21:49.954Z"
                            },
                            "roles": [
                                {
                                "role_id": "67ebe5b4b38db47a3d74253e",
                                "name": "Sim Creator",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "680a65702e304b725c43af35",
                            "first_name": "dwain",
                            "last_name": "Kent",
                            "email": "dkent@c3connect.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Test",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-04-24T16:23:12.827Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-04-24T16:23:12.827Z"
                            },
                            "roles": [
                                {
                                "role_id": "67ebe5b4b38db47a3d74253e",
                                "name": "Sim Creator",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67a31a99aa22bc6b9f0cf551",
                            "first_name": "Nayan",
                            "last_name": "Singhania",
                            "email": "newuser1122@yopmail.com",
                            "phone_no": "",
                            "division": "Test",
                            "department": "Test",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "679a0c3f346f3e2dedaa9738",
                                "name": "Abhinav Pandey"
                                },
                                "time": "2025-02-11T08:56:17.775Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a31a99aa22bc6b9f0cf551",
                                "name": "Nayan Singhania"
                                },
                                "time": "2025-04-28T04:37:03.36Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e174346f3e2dedaa970b",
                                "name": "Manager",
                                "product": "Guidance"
                                },
                                {
                                "role_id": "680efc9aba00ff69f393bd86",
                                "name": "full_access",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67a485479cfbfa3a4a14eb40",
                            "first_name": "Test",
                            "last_name": "Dev1",
                            "email": "pikaneuceuji-5490@yopmail.com",
                            "phone_no": "+22653253332",
                            "division": "EverAI Product",
                            "department": "Product Design VD",
                            "reporting_to": {
                                "id": "67b8104a924ba33c9cf531f1",
                                "name": "Robert Brown"
                            },
                            "hiring_date": "2025-02-21",
                            "class_id": "uhaisu",
                            "internal_user_id": "INT-123INT-123",
                            "external_user_id": "",
                            "status": "ACTIVATION_PENDING",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-02-06T09:47:51.031Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67b47e8590423f138a04232a",
                                "name": "Shivangi Agarwal"
                                },
                                "time": "2025-03-21T12:45:23.703Z"
                            },
                            "roles": [
                                {
                                "role_id": "6799e1fe346f3e2dedaa9710",
                                "name": "tester-1",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67ebe630b38db47a3d74253f",
                            "first_name": "Simulator",
                            "last_name": "Trainee",
                            "email": "simtrainee@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Engineering Dev",
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-01T13:12:16.847Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-01T13:12:16.847Z"
                            },
                            "roles": [
                                {
                                "role_id": "67ebe498b38db47a3d74253d",
                                "name": "Trainee",
                                "product": "Simulator"
                                }
                            ]
                            },
                            {
                            "user_id": "67ebe72cb38db47a3d742543",
                            "first_name": "Simulator",
                            "last_name": "Manager",
                            "email": "simmanager@yopmail.com",
                            "phone_no": "",
                            "division": "EverAI Labs",
                            "department": "Engineering Dev",
                            "reporting_to": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                            },
                            "class_id": "",
                            "internal_user_id": "",
                            "external_user_id": "",
                            "status": "ACTIVE",
                            "created": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-01T13:16:28.386Z"
                            },
                            "updated": {
                                "user": {
                                "id": "67a1188276d6606ab2c082b7",
                                "name": "Maneesh Singh"
                                },
                                "time": "2025-04-30T05:39:20.569Z"
                            },
                            "roles": [
                                {
                                "role_id": "67e11abcab68374a33fd93d0",
                                "name": "Manager",
                                "product": "Simulator"
                                }
                            ]
                            }
                        ]
        
        try:
            for user in users:
                for core_user in core_user_list:
                    if core_user["user_id"] == (user.get("_id") or ""):
                        user_object = {
                            "id": str(core_user.get("user_id")),
                            "name": str(core_user.get("first_name")) + " " + str(core_user.get("last_name")),
                            "email": str(core_user.get("email")),
                            "role": str(core_user.get("roles")[0].get("name")),  # Assuming the first role is the primary role
                            "division": str(core_user.get("division")),
                            "department": str(core_user.get("department")),
                            "addedOn": str(user.get("createdAt")),
                            "status": str(core_user.get("status")),
                            "assignedSimulations": int(0),  # Placeholder value
                            "completionRate": int(0),  # Placeholder value
                            "adherenceRate": int(0),  # Placeholder value
                            "averageScore": int(0),  # Placeholder value
                            "activatedOn": str(core_user.get("created").get("time")),  # Assuming activation on creation
                            "deActivatedOn": str(None),  # Placeholder value
                            "loginCount": int(0),  # Placeholder value
                            "lastLoginOn": str(user.get("lastLoggedInAt") or ""),  # Placeholder value
                            "lastSessionDuration": int(0)  # Placeholder value
                        }
                        assignments_with_stats: FetchAssignedPlansResponse = await self.get_user_assignments_with_stats(
                        user.get("_id"))
                        if assignments_with_stats and assignments_with_stats["data"]:
                            assignmentsData = assignments_with_stats["data"]
                            users_assignments_stats: Stats = assignmentsData.stats
                            if users_assignments_stats and users_assignments_stats.simulation_completed:
                                total_simulations = (
                                    users_assignments_stats.simulation_completed.
                                    total_simulations if users_assignments_stats.
                                    simulation_completed.total_simulations else 0)
                                user_object[
                                    "assignedSimulations"] = int(total_simulations)
                                user_object["completionRate"] = int(math.ceil(
                                    users_assignments_stats.simulation_completed.
                                    percentage))
                            if users_assignments_stats and users_assignments_stats.timely_completion:
                                user_object["adherenceRate"] = int(math.ceil(
                                    users_assignments_stats.timely_completion.
                                    percentage))
                            user_object["averageScore"] = int(math.ceil(
                                users_assignments_stats.average_sim_score))
                            
                        userData.append(
                            AdminDashboardUserActivityResponse(
                                **user_object
                            )
                        )
                        break
            
            return userData
        except Exception as e:
            logger.error(
                f"Error fetching admin dashboard user activity for user_id={user_id}: {str(e)}",
                exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=
                f"Error fetching admin dashboard user activity for user_id={user_id}: {str(e)}")

    async def get_admin_dashboard_user_stats(self, user_id: str) -> AdminDashboardUserActivityStatsResponse:
        try:
            # Add your logic to fetch admin dashboard user stats here
            users_activity = await self.get_admin_dashboard_user_activity(user_id);

            new_users = AdminDashboardUserActivityStatsUserType()
            active_users = AdminDashboardUserActivityStatsUserType()
            deactivated_users = AdminDashboardUserActivityStatsUserType()
            daily_active_users = AdminDashboardUserActivityStatsUserType()
            weekly_active_users = AdminDashboardUserActivityStatsUserType()
            monthly_active_users = AdminDashboardUserActivityStatsUserType()

            for user_activity in users_activity:

                if datetime.strptime(user_activity.addedOn.split()[0], "%Y-%m-%d") == datetime.now().date():
                    new_users.total_users = new_users.total_users + 1
                    if user_activity.role == 'Manager':
                        new_users.breakdown.manager = new_users.breakdown.manager + 1
                    if user_activity.role == 'Admin':
                        new_users.breakdown.manager = new_users.breakdown.admin + 1
                    if user_activity.role == 'Designer':
                        new_users.breakdown.manager = new_users.breakdown.designer + 1
                    if user_activity.role == 'TRAINEE':
                        new_users.breakdown.manager = new_users.breakdown.trainees + 1
                
                if user_activity.status == "ACTIVE":
                    active_users.total_users = active_users.total_users + 1
                    if user_activity.role == 'Manager':
                        active_users.breakdown.manager = active_users.breakdown.manager + 1
                    if user_activity.role == 'Admin':
                        active_users.breakdown.manager = active_users.breakdown.admin + 1
                    if user_activity.role == 'Designer':
                        active_users.breakdown.manager = active_users.breakdown.designer + 1
                    if user_activity.role == 'TRAINEE':
                        active_users.breakdown.manager = active_users.breakdown.trainees + 1

                if user_activity.status == "DEACTIVATED":
                    deactivated_users.total_users = deactivated_users.total_users + 1
                    if user_activity.role == 'Manager':
                        deactivated_users.breakdown.manager = deactivated_users.breakdown.manager + 1
                    if user_activity.role == 'Admin':
                        deactivated_users.breakdown.manager = deactivated_users.breakdown.admin + 1
                    if user_activity.role == 'Designer':
                        deactivated_users.breakdown.manager = deactivated_users.breakdown.designer + 1
                    if user_activity.role == 'TRAINEE':
                        deactivated_users.breakdown.manager = deactivated_users.breakdown.trainees + 1

                if user_activity.lastLoginOn.split()[0] == datetime.now().strftime("%Y-%m-%d"):
                    daily_active_users.total_users = daily_active_users.total_users + 1
                    if user_activity.role == 'Manager':
                        daily_active_users.breakdown.manager = daily_active_users.breakdown.manager + 1
                    if user_activity.role == 'Admin':
                        daily_active_users.breakdown.manager = daily_active_users.breakdown.admin + 1
                    if user_activity.role == 'Designer':
                        daily_active_users.breakdown.manager = daily_active_users.breakdown.designer + 1
                    if user_activity.role == 'TRAINEE':
                        daily_active_users.breakdown.manager = daily_active_users.breakdown.trainees + 1

                if (datetime.now() - datetime.strptime(user_activity.lastLoginOn.split()[0], "%Y-%m-%d")).days < 7:
                    weekly_active_users.total_users = weekly_active_users.total_users + 1
                    if user_activity.role == 'Manager':
                        weekly_active_users.breakdown.manager = weekly_active_users.breakdown.manager + 1
                    if user_activity.role == 'Admin':
                        weekly_active_users.breakdown.manager = weekly_active_users.breakdown.admin + 1
                    if user_activity.role == 'Designer':
                        weekly_active_users.breakdown.manager = weekly_active_users.breakdown.designer + 1
                    if user_activity.role == 'TRAINEE':
                        weekly_active_users.breakdown.manager = weekly_active_users.breakdown.trainees + 1
                
                if (datetime.now() - datetime.strptime(user_activity.lastLoginOn.split()[0], "%Y-%m-%d")).days < 30:
                    monthly_active_users.total_users = monthly_active_users.total_users + 1
                    if user_activity.role == 'Manager':
                        monthly_active_users.breakdown.manager = monthly_active_users.breakdown.manager + 1
                    if user_activity.role == 'Admin':
                        monthly_active_users.breakdown.manager = monthly_active_users.breakdown.admin + 1
                    if user_activity.role == 'Designer':
                        monthly_active_users.breakdown.manager = monthly_active_users.breakdown.designer + 1
                    if user_activity.role == 'TRAINEE':
                        monthly_active_users.breakdown.manager = monthly_active_users.breakdown.trainees + 1
                    
            return AdminDashboardUserActivityStatsResponse(
                new_users=new_users,
                active_users=active_users,
                deactivated_users=deactivated_users,
                daily_active_users=daily_active_users,
                weekly_active_users=weekly_active_users,
                monthly_active_users=monthly_active_users
            )
            
        except Exception as e:
            logger.error(
                f"Error fetching admin dashboard user stats for user_id={user_id}: {str(e)}",
                exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=
                f"Error fetching admin dashboard user stats for user_id={user_id}: {str(e)}")

    async def create_user(self, user_id: str) -> CreateUserResponse:
        logger.info("Creating a new user.")
        logger.debug(f"user_id={user_id}")
        try:
            # Add your logic to create a new user here
            existing_user = await self.db.users.find_one({"_id": user_id})

            if existing_user:
                logger.info(f"User {user_id} already exists.")

                last_logged_in_at = existing_user.get("lastLoggedInAt" or "")
                
                if last_logged_in_at:
                    time_diff = datetime.utcnow() - last_logged_in_at
                else:
                    logger.warning(f"lastLoggedInAt not found for user {user_id}.")
                
                if time_diff.total_seconds() > 86400: 
                    update_result = await self.db.users.update_one(
                        {"_id": user_id},
                        {
                            "$set": {
                                "lastModifiedAt": datetime.utcnow(),
                                "lastLoggedInAt": datetime.utcnow()
                            }
                        }
                    )
                
            else:
                user_doc = {
                    "_id": user_id,
                    "createdAt": datetime.utcnow(),
                    "lastModifiedAt": datetime.utcnow(),
                    "lastLoggedInAt": datetime.utcnow(),
                }
                await self.db.users.insert_one(user_doc)
            return CreateUserResponse(user_id=user_id)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating user: {str(e)}")
