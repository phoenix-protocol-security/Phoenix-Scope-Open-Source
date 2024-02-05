from fastapi import FastAPI, Query, Request
import uvicorn
from modules.hackerone import (
    hackerone,
    hackerone_wildcards,
    hackerone_private,
    hackerone_last_three_months,
)
# from modules.bugcrowd import bugcrowd_programs
from modules.intigriti import (
    intigriti_programs,
    get_bounty_programs_scope,
    get_wildcard_programs_scope,
)
from modules.yeswehack import yeswehack_programs, yeswehack_wildcard_programs
from typing import List, Dict
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import sys


app = FastAPI(
    title="PhoenixScope - API Framework",
    version="1.0",
    description="",
    summary="API to fetch the scope of bug bounty programs listed on various platforms such as HackerOne, BugCrowd, Intigriti, YesWeHack. ",
)
app.mount("/static", StaticFiles(directory="templates"), name="static")
templates = Jinja2Templates(directory="templates")

# Hackerone Endpoints

@app.get("/hackerone/programs", tags=["HackerOne"])
async def get_h1_programs(
    private: bool = Query(False),
    bounty: bool = Query(False),
    wildcards: bool = Query(False),
    mobile_app: bool = Query(False),
    single_domain: bool = Query(False),
    username: str = Query(None),
    token: str = Query(None),
):
    program_json = hackerone(
        username, token, private, bounty, wildcards, mobile_app, single_domain
    )

    return {
        "description": f"Collecting all the programs from H1 of the user {username}.",
        "program_data": program_json,
    }


@app.get("/hackerone/wildcards", tags=["HackerOne"])
async def get_h1_wildcard_programs(
    username: str = Query(None), token: str = Query(None)
):
    program_json = hackerone_wildcards(username, token)

    return {
        "description": f"Collected the wildcard scope domains including public and private for the user {username}",
        "wildcard_domains": program_json,
    }


@app.get("/hackerone/privates", tags=["HackerOne"])
async def get_h1_private_programs(
    username: str = Query(None), token: str = Query(None)
):
    program_json = hackerone_private(username, token)

    return {
        "description": f"Collected the private program for the user {username}",
        "Private Program Details": program_json,
    }


@app.get("/hackerone/latests", tags=["HackerOne"])
async def get_h1_past_three_months_program(
    private: bool = Query(False),
    bounty: bool = Query(False),
    wildcards: bool = Query(False),
    mobile_app: bool = Query(False),
    single_domain: bool = Query(False),
    username: str = Query(None),
    token: str = Query(None),
):
    program_json = hackerone_last_three_months(
        username, token, private, bounty, wildcards, mobile_app, single_domain
    )

    return {
        "description": f"Collected all the past three months programs for the user {username}",
        "Past Three Months Programs Details": program_json,
    }


# BugCrowd Endpoints


# @app.get("/bugcrowd", tags=["Bug Crowd"])
# async def get_bugcrowd_programs(
#     vdp: bool = Query(False),
#     hidden: bool = Query(False),
#     bugcrowd_token: str = Query(None),
# ):
#     program_json = bugcrowd_programs(bugcrowd_token, vdp, hidden)
#     return {
#         "description": f"Collected all the bugcrowd programs",
#         "Programs": program_json,
#     }


# Intigriti Endpoints


@app.get("/intigriti/programs", tags=["Intigriti"])
async def get_intigriti_programs(
    vdp: bool = Query(False),
    hidden: bool = Query(False),
    wildcard: bool = Query(False),
    intigriti_token: str = Query(None),
):
    program_json = intigriti_programs(intigriti_token, vdp, hidden, wildcard)

    return {
        "description": f"Collected all the Intigriti Programs",
        "Programs": program_json,
    }


@app.get("/intigriti/bounty", tags=["Intigriti"])
async def get_intigriti_bounty_programs(
    vdp: bool = Query(False),
    hidden: bool = Query(False),
    intigriti_token: str = Query(None),
):
    program_json = get_bounty_programs_scope(intigriti_token, "all", vdp, hidden)

    return {
        "description": f"Collected all the Intigriti Bounty Programs",
        "Programs": program_json,
    }


@app.get("/intigriti/wildcards", tags=["Intigriti"])
async def get_intigriti_wildcard_scope_programs(
    vdp: bool = Query(False),
    hidden: bool = Query(False),
    intigriti_token: str = Query(None),
):
    program_json = get_wildcard_programs_scope(intigriti_token, "Url", vdp, hidden)

    return {
        "description": f"Collected all the Intigriti Wildcard Scope Programs",
        "Programs": program_json,
    }


# YesWeHack Endpoints


@app.get("/yeswehack/programs", tags=["YesWeHack"])
async def get_ywh_programs(
    vdp: bool = Query(False), hidden: bool = Query(False), ywh_token: str = Query(None)
):
    program_json = yeswehack_programs(ywh_token, vdp, hidden, "all")

    return {
        "description": f"Collected all the YesWeHack Programs",
        "program_data": program_json,
    }


@app.get("/yeswehack/wildcards", tags=["YesWeHack"])
async def get_ywh_wildcard_programs(
    vdp: bool = Query(False), hidden: bool = Query(False), ywh_token: str = Query(None)
):
    program_json = yeswehack_wildcard_programs(ywh_token, vdp, hidden, "url")

    return {
        "description": f"Collected all the YesWeHack Wildcard Scope Programs",
        "Programs": program_json,
    }


# UI Endpoints


@app.get("/", tags=["UI Dashboards"])
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/hackerone", tags=["UI Dashboards"])
async def index(request: Request):
    return templates.TemplateResponse("hackerone.html", {"request": request})


@app.get("/intigriti", tags=["UI Dashboards"])
async def index(request: Request):
    return templates.TemplateResponse("intigriti.html", {"request": request})


@app.get("/ywh", tags=["UI Dashboards"])
async def index(request: Request):
    return templates.TemplateResponse("ywh.html", {"request": request})


@app.get("/bugcrowd", tags=["UI Dashboards"])
async def index(request: Request):
    return templates.TemplateResponse("bugcrowd.html", {"request": request})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    uvicorn.run(app, host="0.0.0.0", port=port)
