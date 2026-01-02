```mermaid
flowchart TB
 subgraph S1[" "]
        B1["Parse CLI args"]
        B2{"Skip unit tests?"}
        B3["Run unit tests"]
        B4["Construct Network from TNTP files"]
        B5["Run net.userEquilibrium"]
        B6["Collect convergence data"]
        B7["Export flows and metrics"]
  end
 subgraph S2[" "]
        C1["Import classes and modules"]
        C2["Load TNTP network and demand files"]
        C3["Call userEquilibrium with parameters"]
        C4["Shortest path and all or nothing assignment"]
        C5["Flow shifting and Frank Wolfe step size"]
        C6["Update link flows and costs"]
        C7["Compute gap metric"]
        C8{"Converged or max iterations?"}
        C9["Finalize solution"]
        C10["Inspect results and metrics"]
  end
 subgraph S3[" "]
        D1["Load base Network"]
        D2["Apply modifiers to capacity demand or links"]
        D3["Re run userEquilibrium"]
        D4["Compute metrics with get_metrics"]
        D5["Compare baseline and policy results"]
  end
 subgraph S4[" "]
        E1["Select protocol files"]
        E2["Run tests run_protocol"]
        E3["Or run tests run_protocol_per_run"]
        E4["Loop over runs and evaluate network"]
        E5["Aggregate or log statistics"]
        E6["Optional compare_networks and compare_results"]
  end
    A0(["Start / Choose Task"]) --> BHeader["Quick Validation - validate.py"] & CHeader["Core UE Solve - network.py"] & DHeader["Policy Analysis - policies and experiments"] & EHeader["Advanced Testing and Benchmarking - tests"]
    BHeader --> B1
    B1 --> B2
    B2 -- No --> B3
    B2 -- Yes --> B4
    B3 --> B4
    B4 --> B5
    B5 --> B6
    B6 --> B7
    CHeader --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> C5
    C5 --> C6
    C6 --> C7
    C7 --> C8
    C8 -- No --> C3
    C8 -- Yes --> C9
    C9 --> C10
    DHeader --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> D5
    EHeader --> E1
    E1 --> E2 & E3
    E2 --> E4
    E3 --> E4
    E4 --> E5
    E5 --> E6

     C2:::Rose
     CHeader:::Pine
     DHeader:::Sky
    classDef Pine stroke-width:1px, stroke-dasharray:none, stroke:#254336, fill:#27654A, color:#FFFFFF
    classDef Sky stroke-width:1px, stroke-dasharray:none, stroke:#374D7C, fill:#E2EBFF, color:#374D7C
    classDef Rose stroke-width:1px, stroke-dasharray:none, stroke:#FF5978, fill:#FFDFE5, color:#8E2236
