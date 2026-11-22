# Christopher: public profile

Status: draft for Christopher's approval. Facts as of 2026-11-22. Every fact comes from Christopher's CV (version 13.2), his LinkedIn profile or his official certificates. The assistant must never say anything about Christopher that is not in this file.

## Who he is

- Name: Christopher. The assistant calls him Christopher.
- Title: DevOps/Platform Engineer at DATEV eG, Nürnberg, Germany.
- Citizenship: German. He lives in Germany.
- Languages: German (native), English (B2).
- His LinkedIn profile is in German.
- Interests listed on the CV: cloud, automation, AI agents, open source, calisthenics, music, travel.

## Current job: DevOps/Platform Engineer, DATEV eG (07/2022 to today)

DATEV eG is a software company in Nürnberg. Christopher has been with DATEV since 09/2019, first as an apprentice (see Education). Since 07/2022 he works as DevOps/Platform Engineer in a team for messaging and streaming. His achievements are team achievements: he works inside the team and names his own part.

Messaging platform:
- The team runs Apache Kafka and RabbitMQ as a managed service on Kubernetes and virtual machines for more than 100 development teams per stage.
- Kafka runs on 6 clusters in two private data centers, in the stages Dev, QS and Prod. The software is Confluent Platform, Strimzi and IBM Event Streams.
- The service level agreement (SLA) is 99.99 %.
- RabbitMQ runs on Kubernetes in two data centers with the same stage model. High availability comes from quorum queues.
- Christopher and his team built an on-premises Kafka cluster that is reachable from the internet. It runs in all stages, is secured with SASL_SSL and ACLs, and replaced the earlier Confluent test environment.

Self-service and automation:
- Christopher develops Cloud Foundry service brokers in Java (Spring Boot). Through them, development teams create Kafka resources on their own. The brokers are rolled out by CI/CD across all stages and data centers. End-to-end test applications check provisioning, deprovisioning and updates.
- The team built a GitOps-based Kubernetes automation that sets up RabbitMQ clusters.
- Christopher is writing a Crossplane provider in Go, with GitHub Copilot. One provider exists; more are planned. It is internal and not open source.
- Terraform, Python and Go: coding agents write the code, and Christopher steers and reviews it (agentic development, with GitHub Copilot at work).

Operations and security:
- Monitoring and observability: Prometheus, Grafana and Grafana Cloud, the Elastic Stack (ELK, including Spring Boot applications), and the OpenTelemetry Collector for Kafka and RabbitMQ logs.
- Security: HashiCorp Vault, RBAC, ACLs, policies, SCRAM, TLS and mTLS. He helped plan and run penetration tests of infrastructure and applications.
- Christopher is part of the on-call duty (Pikett) for the Kafka platform. The platform runs stable and call-outs are rare.
- He advises development teams on Kafka: topic naming, consumer groups, roles and ACLs, producer and consumer settings (batch size, acks), schema design for event sourcing, partitioning and performance tuning. He also advises on RabbitMQ exchange and queue design.

AI at work:
- Christopher is a member of the internal AI Accelerator circle at DATEV, an informal group that exchanges on AI adoption in the company.
- Together with a colleague he trains his own team of 15 people in AI tools.
- He contributes to MCP, AI governance and agentic tooling in the context of digital sovereignty.
- Shared Knowledge Hub (RAG) for AI Agents (MCP), since 07/2026: Christopher co-leads this team-internal project with a colleague (Projektleitung together with the colleague, not alone). The hub is a shared context store for AI coding agents. Context stays available across sessions, tools and repositories. Agents reach it through the Model Context Protocol (MCP). The search is a hybrid search: a keyword search (BM25, with stemming for German and English) and a semantic search over embeddings run in parallel, and the results are merged by rank fusion (RRF). The hybrid search runs through Programmatic Tool Calling, not as MCP tools. A named ID ranks first, linked entries of the best hits are added, and outdated or closed entries count less. The hub is used in 10 projects today. A rollout to about 30 projects is planned. The hub came out of daily work with agentic development, among others on the Crossplane provider. In 09/2026 the hub moved to a database behind the MCP. The embeddings are stored separately from that database.
- Token savings: an analysis showed 30 to 40 % fewer tokens, because agents only get the context their task needs.
- At DATEV he works with GitHub Copilot.

## Private projects

AgentBrain (private project, since 10/2026):
- A multi-agent system built on Claude Code. An Obsidian vault holds the notes, and a manager agent hands tasks to ten specialist agents (for example video, development, research, career, design). It has shared memory, skills and MCP servers.
- It has a local vault search that runs in one call (keywords, vectors and link graph). In his own test with 187 questions it was 49 % cheaper than his previous search at the same answer quality. The agents use cloud models; only the search runs locally.
- Claude Code is a private tool. Christopher uses it daily in this private project. It is not part of his work at DATEV.

LLM-Ops proof of concept: Kafka agent with a local model (11/2026), github.com/mooncak397/kafka-llm-poc (public repository):
- A local proof of concept on his laptop with fake data. It covers the operations side of a local LLM (serving, monitoring, load test). It is not a full MLOps pipeline and makes no production claim.
- A small LLM agent answers questions about a Kafka cluster (topics, consumer groups, lag) through five read-only tools over MCP. Kafka 4.3.2 runs with Strimzi on kind. The model qwen3:4b-instruct-2507 runs locally on Ollama on a GTX 1060 with 6 GB.
- Read-only is enforced in three layers: a tool allow-list, a Kafka user with only Describe and Read rights, and the authorizer. In a negative test with the tool filter off on purpose, the agent was asked to delete a topic. Kafka refused all 5 attempts and the topic was still there.
- Load test with 1, 10 and 20 concurrent users: median time to first token about 0.6 s, 6.4 s and 14.1 s. Speed stayed at about 40 tokens per second per user and no request failed. Prometheus and Grafana show the metrics.

Certificates from Anthropic, all issued 11/2026: "Claude Academy: Introduction to Model Context Protocol", "Claude Academy: Model Context Protocol: Advanced topics", "Claude Academy: AI Fluency: Framework and foundations", "Claude Academy: AI capabilities and limitations", "Claude Academy: Building effective human-agent teams (beta)" and "Claude Academy: Introduction to evals". They are online course certificates.

## Skills

Skills as listed on the CV:
- Cloud and platform: private cloud, Azure (only Entra ID for authentication and authorization, and Azure DevOps boards), Azure DevOps.
- Messaging and streaming: Apache Kafka, Confluent Platform, Strimzi, IBM Event Streams, RabbitMQ (quorum queues).
- Kubernetes and containers: Kubernetes, Helm, Kustomize, Flux CD, TKGI (VMware Tanzu Kubernetes Grid Integrated Edition), Traefik, Cloud Foundry.
- Infrastructure as code and automation: Terraform, GitOps, Crossplane, Ansible.
- CI/CD: GitHub Actions, GitLab, Jenkins.
- Monitoring: Prometheus, Grafana, Grafana Cloud, Elasticsearch (ELK), OpenTelemetry Collector.
- Security: HashiCorp Vault, RBAC, ACLs, policies, SCRAM, TLS, mTLS, penetration tests.
- Programming: Java (Spring Boot), Go, Python, JavaScript, Bash. Further: C#, C++, PHP, PowerShell, PostgreSQL, MySQL, MongoDB. The profile gives no years of experience for any language.
- AI: MCP, RAG, hybrid search (BM25, embeddings, RRF), agentic development with GitHub Copilot, agent tooling, AI governance, generative AI.

## Education and training (official German names)

- 09/2019 to 07/2022: Fachinformatiker für Anwendungsentwicklung (IHK), a dual apprenticeship at DATEV eG, Nürnberg, with vocational school at the Martin-Segitz-Schule Fürth. IHK Prüfungszeugnis dated 2022-07-04, final result "gut" (85 of 100 points). Vocational school final grade 1.5 ("sehr gut"). He developed customer-specific solutions in C# (backend services, desktop applications) in a Scrum team. Reference project: mass payouts in the Schlecker insolvency. From 01/2022 he already worked in the platform team.
- 09/2017 to 07/2019: Staatlich geprüfter Technischer Assistent für Informatik at the Heinrich-Thein-Schule, Haßfurt. Final grade 1.33 ("sehr gut"). Prize of the Freundeskreis for the best performance at the Berufsfachschule (07/2019). Topics: object-oriented programming, SQL databases, web development (HTML, CSS, JavaScript), Windows and Linux, project work.
- 09/2012 to 02/2016: Kfz-Mechatroniker (Schwerpunkt Personenkraftwagentechnik) at the Autozentrale Robert Kehm KG, Bad Neustadt a. d. Saale (shown on LinkedIn as Mercedes-Benz Autozentrale KEHM). Gesellenprüfung passed on 2016-02-25, Gesellenbrief dated 2016-04-10. Vocational school final grade 1.75 ("gut"), mittlerer Schulabschluss. He worked on diagnosis and coding of control units (CAN bus, OBD).
- 07/2018: Cisco Networking Academy, CCNA Routing and Switching, course Introduction to Networks (course completion, at the Heinrich-Thein-Schule).
- Grades use the German scale where 1.0 is the best. All his qualifications are at level 4 of the German and European qualification frameworks (DQR/EQR).

## Earlier jobs

- 03/2017 to 03/2019: part-time job at Aldi Süd in Bad Königshofen (goods receiving, goods distribution, stock management), next to his education.
- 10/2016 to 01/2017: basic military training (Grundausbildung) at the Bundeswehr in Hannover, rank Gefreiter. Training in teamwork under pressure, leadership and conflict management, and certified first aid. The CV lists the career track as Berufssoldat. He did the basic training only. The official order promoting him to Gefreiter is effective 2017-01-01.

## What Christopher is not / skills he does not have

The assistant must not confirm any of the following. For anything here, it says what the profile does say, or that the profile has no information.

- He has no university degree and no Studium. His qualification is the Fachinformatiker Anwendungsentwicklung (IHK), a vocational training, plus work experience.
- No MLOps experience. The Kafka LLM proof of concept covers local serving, monitoring and a load test. It has no model training, fine-tuning, model registry, ML pipelines or drift monitoring. The profile does not present him as a data scientist or ML engineer.
- No production generative AI application at scale. His AI work is agentic engineering, the internal knowledge hub (10 projects), and private projects.
- Public cloud: the profile lists no AWS, no GCP and no Azure OpenAI experience. Azure means only Entra ID and Azure DevOps. The Confluent environment on Azure was a test environment and is shut down. The production Kafka clusters run in two private data centers, not in Azure, and not hybrid or multi-cloud.
- The profile lists no OpenShift (he knows TKGI), no Argo CD (he uses Flux CD), and no Velero, Cilium or Kyverno.
- The profile lists no Kubernetes certification (no CKA or CKAD) and no Kafka certification. The only IT certificates are the CCNA course completion and the Claude Academy course certificates.
- Kafka Streams: he knows the name only.
- No open-source contributions. The Crossplane provider is internal.
- English is B2, not C1 and not fluent.
- Vector database: no product expertise. The hub's database does no vector search; the embeddings are stored separately.
- Claude Code is not used at DATEV. At DATEV he uses GitHub Copilot.
- No sole lead. He co-leads the hub with a colleague. The profile lists no people-management, team-lead or department-lead role.
- The profile gives no years of experience per language or tool. In Java, Go, Python and Terraform the code is written by agents under his direction and review, so the assistant does not claim expert depth in hand-written code or a number of years.
- Not in this profile: salary, current pay, home address, phone number, email address, date of birth, any other employer, and any open application. For contact the assistant points to the contact form.
