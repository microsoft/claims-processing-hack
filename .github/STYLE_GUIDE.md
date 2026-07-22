# Documentation Style Guide

This guide ensures consistent formatting across all hackathon documentation.

## Text Formatting Conventions

| Style | Use for | Examples |
|-------|---------|----------|
| **Bold** | Product names, service names, agent names, important terms on first use | **Azure**, **Cosmos DB**, **GitHub Codespaces**, **Anomaly Detection Agent** |
| *Italic* | UI labels, buttons, menu items, emphasis, conceptual terms | Click *Fork*, select the *Code* tab, both *proactive* and *reactive* maintenance |
| `Code fence` | File names, commands, code references, environment variables, technical identifiers | `seed-data.sh`, `Program.cs`, `COSMOS_ENDPOINT`, `machine-001` |

## Detailed Guidelines

### Bold

Use **bold** for:

- Product and service names: **Azure**, **Cosmos DB**, **GitHub Codespaces**, **API Management**
- Agent names: **Anomaly Detection Agent**, **Fault Diagnosis Agent**, **Repair Planner Agent**
- Important terms on first use: **Overall Equipment Effectiveness (OEE)**
- Key concepts being introduced: **predictive maintenance**, **multi-agent system**

Do **not** bold common technical terms that appear frequently, such as:

- Programming languages: .NET, C#, Python, JavaScript, TypeScript
- Frameworks and runtimes: Node.js, React, ASP.NET
- General technical concepts: API, SDK, JSON, HTTP

### Italic

Use *italic* for:

- UI elements (buttons, menus, tabs): Click the *Fork* button, select the *Data Explorer* tab
- Emphasis within a sentence: Technicians perform both *proactive* and *reactive* maintenance
- Conceptual terms being highlighted: The system uses *condition-based* monitoring

### Hyperlinks

Do **not** apply formatting (bold, italic, code) inside link text. Keep link text plain for readability and consistency.

#### ❌ Incorrect

```markdown
- [Custom agents in **VS Code**](https://example.com)
- [Learn about `CosmosDbService`](https://example.com)
```

#### ✅ Correct

```markdown
- [Custom agents in VS Code](https://example.com)
- [Learn about CosmosDbService](https://example.com)
```

### Code Fence

Use `code fence` for:

- File names: `README.md`, `Program.cs`, `azuredeploy.json`
- Script names: `seed-data.sh`, `get-keys.sh`
- Commands: `az login`, `dotnet build`
- Environment variables: `COSMOS_ENDPOINT`, `$RESOURCE_GROUP`
- Database/container names: `FactoryOpsDB`, `Machines`, `Telemetry`
- IDs and partition keys: `machine-001`, `/machineType`
- Class names and code references: `FaultMappingService`, `AgentClient`
- Configuration values: `swedencentral`, `tire_curing_press`

## Examples

### ❌ Incorrect

```markdown
Run the seed-data.sh script to populate Cosmos DB.
Click on the Fork button to create your copy.
The COSMOS_ENDPOINT variable must be set.
```

### ✅ Correct

```markdown
Run the `seed-data.sh` script to populate **Cosmos DB**.
Click the *Fork* button to create your copy.
The `COSMOS_ENDPOINT` variable must be set.
```

## Quick Reference

| Item | Style | Example |
|------|-------|---------|
| Azure service | **Bold** | **Cosmos DB** |
| Agent name | **Bold** | **Fault Diagnosis Agent** |
| Button/menu | *Italic* | Click *Deploy* |
| Emphasis | *Italic* | *proactive* maintenance |
| File name | `Code` | `README.md` |
| Command | `Code` | `az login` |
| Environment variable | `Code` | `COSMOS_ENDPOINT` |
| Container/database | `Code` | `Machines` |
| ID/key | `Code` | `machine-001` |

## Challenge README Structure

Each challenge README follows a consistent structure with the following sections in order:

### Required Sections

| Order | Section | Emoji | Purpose |
|-------|---------|-------|---------|
| 1 | **Header** | — | Title, welcome, description, duration, prerequisites |
| 2 | **Objective** | 🎯 | Bullet list of learning goals |
| 3 | **Context and Background** | 🧭 | Scenario diagram, technical concepts, architecture |
| 4 | **Tasks** | ✅ | Step-by-step instructions |
| 5 | **Go Further** | 🚀 | Optional stretch goals (with NOTE callout) |
| 6 | **Troubleshooting and FAQ** | 🛠️ | Collapsible problem/solution pairs |
| 7 | **Conclusion and Reflection** | 🧠 | Recap, architecture diagram, key takeaways, further reading |

### Header Format

```markdown
# Challenge N: Title

Welcome to Challenge N!

Brief description of what the challenge covers.

**Expected duration**: XX min  
**Prerequisites**: [Challenge N-1](../challenge-N-1/README.md) successfully completed
```

### Section Templates

#### Objective
```markdown
## 🎯 Objective

The goals for this challenge are:

- First goal
- Second goal
- Third goal
```

#### Go Further
```markdown
## 🚀 Go Further

> [!NOTE]
> Finished early? These tasks are **optional** extras for exploration. Feel free to move on to the next challenge — you can always come back later!

### Optional Task Title
Description of optional exploration task.
```

#### Tasks
```markdown
## ✅ Tasks

### Task 1: First task title
Instructions for the first task.

### Task 2: Second task title
Instructions for the second task.

🎉 Congratulations! You've successfully completed Challenge N.
```

> [!NOTE]
> Place the congratulations message at the **end of the Tasks section**, not in the Conclusion.

#### Troubleshooting
```markdown
## 🛠️ Troubleshooting and FAQ

<details>
<summary>Problem: Description of the problem</summary>

Solution or explanation here.

</details>
```

#### Conclusion
```markdown
## 🧠 Conclusion and Reflection

🎉 Congratulations! Summary of what was accomplished.

Key takeaways or reflection points.

---

If you want to expand your knowledge on what we've covered in this challenge, have a look at the content below:

- [Link title](url)
```

## Numbered Callouts for Diagrams

When explaining numbered elements in diagrams (e.g., architecture diagrams, flow diagrams), use **filled circled numbers** for better readability:

| Number | Symbol | Unicode |
|--------|--------|--------|
| 1 | ❶ | U+2776 |
| 2 | ❷ | U+2777 |
| 3 | ❸ | U+2778 |
| 4 | ❹ | U+2779 |
| 5 | ❺ | U+277A |
| 6 | ❻ | U+277B |
| 7 | ❼ | U+277C |
| 8 | ❽ | U+277D |
| 9 | ❾ | U+277E |
| 10 | ❿ | U+277F |

### Usage

- Use filled circled numbers when referencing numbered callouts in diagrams
- **Bold the circled numbers** when used in tables for better visibility (e.g., `| **❶** | Description |`)
- Each numbered item should be on its own paragraph (add blank line between items)
- Numbers in diagrams should match the filled style for visual consistency

### Example

In prose/paragraphs:

```markdown
![Architecture diagram](./images/architecture.png)

❶ The user submits a request to the API gateway.

❷ The gateway routes the request to the appropriate service.

❸ The service processes the request and returns a response.
```

In tables (use bold):

```markdown
| # | Component | Description |
|---|-----------|-------------|
| **❶** | **API Gateway** | Routes incoming requests to services |
| **❷** | **Backend Service** | Processes the request |
```

## Color scheme
The colors are based on **GitHub Dark Default** theme

### Base surfaces
- **Background:** `#0D1117`
- **Surface 1 (system container fill):** `#161B22`
- **Surface 2 (alt surface / inner panels):** `#21262D`
- **Generic border/divider:** `#30363D`

### Text
- **Primary (titles):** `#E6EDF3`
- **Normal (most labels):** `#C9D1D9`
- **Muted (de-emphasized labels):** `#8B949E`

### Headings
- **H1 (diagram title):** `#E6EDF3`
- **H2 (main systems):** `#C9D1D9`
- **H3 (main components):** `#C9D1D9`
- **H4 (small icon labels):** `#8B949E`

### Icons (fixed constraint)
- **Icon color (unchanged):** `#959CBD`

---

### Containers / canvases

#### Main canvas (outer diagram box)
- **Fill:** `#0D1117` (or transparent)
- **Border:** `#30363D`

#### System containers (GitHub / Azure / etc.)
- **Fill:** `#161B22`
- **Border:** `#30363D`
- **Accent border/strip (system-specific):**
  - **GitHub:** `#58A6FF`
  - **Azure:** `#2F81F7`
  - **Generic (non-specific):** `#8B949E` *(neutral)*
    - Alternative generic accent (more “active”): `#A371F7`

#### Component boxes (high-contrast)
- **Fill:** `#1B2028`
- **Border:** `#3D444D`
- **Title text:** `#E6EDF3`
- **Small label / footnote:** `#C9D1D9` *(keep secondary via smaller size/weight)*

---

### Arrows & labels
- **Main arrows (primary flows):**
  - Stroke: `#58A6FF`
  - Label: `#C9D1D9` *(or `#58A6FF` to match stroke)*
- **Secondary arrows (dotted dependencies):**
  - Stroke: `#8B949E`
  - Label: `#8B949E`
- **Critical path (optional):**
  - Stroke: `#F85149`
  - Label: `#F85149` *(or `#C9D1D9` if readability needs it)*

---

### Number callouts (green)
- **Badge fill:** `#3FB950`
- **Badge text:** `#0D1117`
- **Badge border:** `#30363D`

---

### Accent mapping (general)
| Accent | Hex | Typical use |
|---|---:|---|
| Blue | `#58A6FF` | Primary flows, APIs, GitHub highlights |
| Deep blue | `#2F81F7` | Azure highlights / alternate primary |
| Green | `#3FB950` | Success/happy path, callout numbers |
| Amber | `#D29922` | Warnings, attention, manual steps |
| Red | `#F85149` | Failures, critical paths |
| Purple/Magenta | `#A371F7` | Observability, async/events, special systems |
| Neutral gray | `#8B949E` | Secondary dependencies, informational links |

