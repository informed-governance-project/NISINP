Governance Platform project news
================================


##  0.1.4 (2024-02-27)

### Changes

- Fix issue on workflow saving : prevent to have two incident report with the same position #113
- Remove green message when saving is not done on company (#73) and sector tab
- Some security additions to prevent unauthorized people to access incident
- Add CERT role #105
- Fix user list for operator admin in admin view #118


##  0.1.3 (2024-02-14)

### Changes

- Fix issue in the save of Email template
- Put the country field in a dropdown in admin panel #53
- Change the title of the comment's modal #108
- Update dependencies
- Add creator for some entities #54
- Incident Report -> Impacts : don't show unsectorized impacts, and improve display #107
- Fix issue on detection date #106
- Send email to the regulator #104
- Email remove default signature and headers (in the theme repository)
- Huge database structure modification to solve #50
  (**need to retest all the application (user/sector/companies)**)
- Improve layout for operator's incident list view #111
- Add regulation filter when fetching impact in incident report (commit : 193c41f)
- Put the timeline in all the report #112 (**Major change : retest workflow**)
- Replace dropdown by label in regulator view for country list #109
- Fix issue with sector saving (commit : aea80fc)
- Add all the report in the incident list of operator #100


## 0.1.2 (2024-02-01)

### Changes

- Fix issue with Region/Country list question
- Reset the counter of incident id to 0 when the year changed
- Group the impact by sector/subsector in the impact form for operator
- Add pagination in the incident list
- Fix issue with date filtering


## 0.1.1 (2024-01-26)

### Changes

- add filtering in incident list #88
- first draft to see the history in regulator incident view
- Fix issue in incident report #99
- Fix significative impact #96
- Change impacts in administration view #93
- Add headline for email #94
- Add significative impact for operator in the incident list #21
- change checkbox for the first form to a slider #97
- Fix PDF generation #91
- Add review comment for each workflow, add the comment in the operator side #71
- Fix issue with impacts in the regulator's incident view #95
- Make the deletion of companies with users impossible #73
- Start improving the view of sector displaying (Order and indent)
  (not finished yet) and some business logic improvement #65


## 0.1.0 (2023-09-06)

Preliminary and final notification form to test.
