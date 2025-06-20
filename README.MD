# ORATOR 🗣️ : THE ONLY WAY TO LISTEN TO PDFs AND EPUBs
![](/Users/kayparmar/Desktop/code/Projects/ORATOR/System_Design.png)
## <ins>Outline<ins>
- [ORATOR 🗣️ : THE ONLY WAY TO LISTEN TO PDFs AND EPUBs](#orator-️--the-only-way-to-listen-to-pdfs-and-epubs)
  - [Outline](#outline)
    - [What is the problem at hand?](#what-is-the-problem-at-hand)
    - [TECH STACK](#tech-stack)
    - [Core Use-Cases \& User Stories](#core-use-cases--user-stories)
    - [Vague milestones](#vague-milestones)
- [Development Style](#development-style)
    - [Sponsor me \<3](#sponsor-me-3)



### What is the problem at hand? 
  - there is no app/ tool that converts pdf's for e.g books, to an audible format, extracting all the utilities a pdf reader could such as Outline navigation (if and when an Index or Outline is provided), bookmarking, continue where you left off etc.
  - Making sure this thing is free and free of virues/ malware. 
  
### TECH STACK
- FRONT-END: REACT JS 
- BACK-END: PYTHON
  - DATABASE: SQL
  - MACHINE-LEARNING: For zero-shot tts (text-to-speech)

###  Core Use-Cases & User Stories
| Priority | User story                                     | Why it matters for MVP                       |
| -------- | ---------------------------------------------- | -------------------------------------------- |
| 1        | **Upload PDF ➜ get playable audio**            | Must-have loop that proves value.            |
| 2        | **Stream progress (“25 %, extracting text…”)** | Keeps users confident during heavy jobs.     |
| 3        | **Download/stream MP3**                        | Lets users listen offline & on any device.   |
| 4        | **Save job history / resume**                  | Enables multi-session use and accounts.      |
| 5        | **Multi-voice & language options**             | Early differentiator once basics are stable. |






### Vague milestones
| Week    | Deliverable                                              | Success metric                             |
| ------- | -------------------------------------------------------- | ------------------------------------------ |
| **1**   | Bare-bones upload ➜ sync TTS ➜ return MP3                | A PDF converts on localhost in < 2 min     |
| **2**   | Docker Compose (FastAPI, Redis, Celery, Postgres, MinIO) | `docker compose up` yields working loop    |
| **3**   | React drag-and-drop, progress polling                    | UI shows real progress for 3 MB PDF        |
| **4**   | User accounts & job history                              | Two users see only their own jobs          |
| **5**   | Multi-voice dropdown, language auto-detect               | Spanish PDF speaks Spanish                 |
| **6**   | Deploy to Fly.io or Render                               | Public URL converts < 5 MB PDFs reliably   |
| **7–8** | Harden (retry logic, logging, alerts)                    | 99 % jobs succeed in staging               |
| **TBD** | Scale‐out: Kubernetes or AWS Fargate, CDN, SSO, paywall  | Handles 1k concurrent jobs, < 5 s API p-95 |

# Development Style
> https://en.wikipedia.org/wiki/Twelve-Factor_App_methodology
> <table class="wikitable" style="text-align:left">
<caption>The Twelve Factors<sup id="cite_ref-Red1_1-2" class="reference"><a href="#cite_note-Red1-1"><span class="cite-bracket">[</span>1<span class="cite-bracket">]</span></a></sup><sup id="cite_ref-The12_2-0" class="reference"><a href="#cite_note-The12-2"><span class="cite-bracket">[</span>2<span class="cite-bracket">]</span></a></sup>
</caption>
<tbody><tr>
<th>#</th>
<th>Factor</th>
<th>Description
</th></tr>
<tr>
<td>I</td>
<td>Codebase</td>
<td>There should be exactly one codebase for a deployed service with the codebase being used for many deployments.
</td></tr>
<tr>
<td>II</td>
<td>Dependencies</td>
<td>All dependencies should be declared, with no implicit reliance on system tools or libraries.
</td></tr>
<tr>
<td>III</td>
<td>Config</td>
<td>Configuration that varies between deployments should be stored in the environment.
</td></tr>
<tr>
<td>IV</td>
<td>Backing services</td>
<td>All backing services are treated as attached resources and attached and detached by the execution environment.
</td></tr>
<tr>
<td>V</td>
<td>Build, release, run</td>
<td>The delivery pipeline should strictly consist of build, release, run.
</td></tr>
<tr>
<td>VI</td>
<td>Processes</td>
<td>Applications should be deployed as one or more stateless processes with persisted data stored on a backing service.
</td></tr>
<tr>
<td>VII</td>
<td><a href="/wiki/Port_(computer_networking)" title="Port (computer networking)">Port</a> binding</td>
<td>Self-contained services should make themselves available to other services by specified ports.
</td></tr>
<tr>
<td>VIII</td>
<td><a href="/wiki/Concurrent_computing" title="Concurrent computing">Concurrency</a></td>
<td>Concurrency is advocated by scaling individual processes.
</td></tr>
<tr>
<td>IX</td>
<td>Disposability</td>
<td>Fast startup and shutdown are advocated for a more robust and resilient system.
</td></tr>
<tr>
<td>X</td>
<td>Dev/Prod parity</td>
<td>All environments should be as similar as possible.
</td></tr>
<tr>
<td>XI</td>
<td>Logs</td>
<td>Applications should produce logs as event streams and leave the execution environment to aggregate.
</td></tr>
<tr>
<td>XII</td>
<td>Admin Processes</td>
<td>Any needed admin tasks should be kept in source control and packaged with the application.
</td></tr></tbody></table>

### Sponsor me <3
https://github.com/sponsors/kayo09/