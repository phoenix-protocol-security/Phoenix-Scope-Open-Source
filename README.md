# Phoenix-Scope-Open-Source

## Description

A microservice application that provides an APIs to fetch the scope of bug bounty programs listed on various platforms such as HackerOne, BugCrowd, Intigriti, and YesWeHack, as well as UI dashboards to view the data.

## Features

- Covers 4 Bug Bounty Platforms
  - HackerOne
  - Bug Crowd
  - Intigriti
  - Yes We Hack
- Ability to create Custom Monitoring Alerts for Scope Changes for any Program avaialable on any Platform
- Basic Asset Enumeration for any program requested by user with details shared over slack, discord, telegram and pushbullets.
- Multiple filters to get the specific type of scope and type of program such as programs with only wildcard scopes, private programs with url scope, etc.

## Roadmap

- Deployed on AWS, current version is only helpful for getting the data for specific platform based on the API token and username(For H1 only) provided.
- Version 1.2 includes the Basic Asset Enumeration and Alert features on the dashboard itself.
- Version 2.0 includes monitoring and custome alerts for scope changes.
