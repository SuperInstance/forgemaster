Here is the complete BNF grammar for the GUARD constraint language in EBNF notation:

```
constraint ::= range_constraint | domain_constraint | exact_match | logical_combinator | temporal | security | group | metadata

range_constraint ::= identifier "in" "[" numeric_literal "," numeric_literal "]"
domain_constraint ::= identifier "in" "domain" hex_literal
exact_match ::= identifier "equals" numeric_literal

logical_combinator ::= constraint "AND" constraint | constraint "OR" constraint | "NOT" constraint | constraint "IMPLIES" constraint

temporal ::= "WITHIN" numeric_literal "CYCLES" | "STABLE" "FOR" numeric_literal | "DEADLINE" numeric_literal

security ::= "REQUIRES" "capability" | "SANDBOX" "{" constraint_list "}"

group ::= "constraint_group" identifier "{" constraint_list "}"

metadata ::= "@" identifier "(" identifier ")"

constraint_list ::= constraint | constraint ";" constraint_list

type_annotation ::= identifier ":" type

type ::= "int32" | "bitmask" "(" numeric_literal ")"

comment ::= "#" text

guard_file ::= (comment | type_annotation | constraint | group | metadata)*
```

Examples for each production rule:

1. Range constraint: `x in [0, 100]`
2. Domain constraint: `y in domain 0xFF`
3. Exact match: `z equals 42`
4. Logical combinators:
   - `a AND b`
   - `c OR d`
   - `NOT e`
   - `f IMPLIES g`
5. Temporal:
   - `WITHIN 10 CYCLES`
   - `STABLE FOR 5`
   - `DEADLINE 100`
6. Security:
   - `REQUIRES capability`
   - `SANDBOX { x in [0, 10]; y in domain 0xF }`
7. Group: `constraint_group safety { x in [0, 100]; y in domain 0xFF }`
8. Metadata: `@priority(HIGH)`
9. Comment: `# This is a line comment`
10. Type annotations: `x: int32`, `y: bitmask(8)`

Complete syntax for a .guard file specifying an eVTOL flight envelope:

```guard
# eVTOL Flight Envelope Constraints

@priority(HIGH)
@safety(DAL_A)

altitude: int32
velocity: int32
acceleration: int32

constraint_group flight_envelope {
    altitude in [0, 10000]
    velocity in [0, 200]
    acceleration in [-10, 10]
    
    STABLE FOR 5
    DEADLINE 100
    
    REQUIRES capability
}
```

This .guard file defines an eVTOL flight envelope with constraints on altitude, velocity, and acceleration. It specifies the ranges for each parameter and includes temporal requirements for stability and deadline. The safety classification is set to DAL_A, and the constraints are grouped together in a named constraint group. The file also includes type annotations for the variables and a security requirement.