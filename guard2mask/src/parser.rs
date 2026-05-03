use nom::{
    IResult, bytes::complete::{tag, take_while, take_while1}, character::complete::{alpha1, digit1, multispace0, multispace1}, 
    sequence::{delimited, preceded, tuple}, combinator::{map, map_res, recognize, value}, branch::alt,
    multi::{fold_many0, many0, separated_list0},
};
use thiserror::Error;

#[derive(Debug, PartialEq)]
pub enum Priority {
    Hard,
    Soft,
}

#[derive(Debug, PartialEq)]
pub enum Check {
    Range { start: f64, end: f64 },
    Whitelist(Vec<String>),
    Bitmask(u32),
    Thermal(f64),
    Sparsity(u32),
}

#[derive(Debug, PartialEq)]
pub struct Constraint {
    pub name: String,
    pub priority: Priority,
    pub checks: Vec<Check>,
}

#[derive(Debug, PartialEq)]
pub struct ConstraintGroup {
    pub name: String,
    pub require_all: bool,
    pub constraints: Vec<String>,
}

#[derive(Debug, PartialEq)]
pub struct OverrideDecl {
    pub constraint: String,
    pub over: String,
}

#[derive(Debug, PartialEq)]
pub struct WeakenDecl {
    pub range: (f64, f64),
}

#[derive(Debug, PartialEq)]
pub enum GuardItem {
    Constraint(Constraint),
    ConstraintGroup(ConstraintGroup),
    Override(OverrideDecl),
    Weaken(WeakenDecl),
}

#[derive(Debug, Error)]
pub enum ParseError {
    #[error("invalid constraint priority")]
    InvalidPriority,
    #[error("invalid check type")]
    InvalidCheckType,
    #[error("invalid number")]
    InvalidNumber,
    #[error("invalid identifier")]
    InvalidIdentifier,
    #[error("unexpected token")]
    UnexpectedToken,
}

fn parse_priority(input: &str) -> IResult<&str, Priority> {
    alt((
        value(Priority::Hard, tag("HARD")),
        value(Priority::Soft, tag("SOFT")),
    ))(input)
}

fn parse_check(input: &str) -> IResult<&str, Check> {
    alt((
        map(
            tuple((
                tag("range"),
                delimited(tag("("), map_res(recognize!(tuple((fold_many0!(preceded!(multispace1, map_res(digit1, str::parse::<f64>)), alt!((tag("+"), value(1)), (tag("-"), value(-1))))), (multispace0, tag(","), multispace0, map_res(digit1, str::parse::<f64>)))), tag(")")),
            )),
            |(start, end)| Check::Range { start, end },
        ),
        map(
            tuple((
                tag("whitelist"),
                delimited(tag("("), map(separated_list0!(tag(","), alpha1), |v| v.into_iter().map(String::from).collect()), tag(")")),
            )),
            |v| Check::Whitelist(v),
        ),
        map(
            tuple((
                tag("bitmask"),
                delimited(tag("("), map_res(digit1, str::parse::<u32>), tag(")")),
            )),
            |v| Check::Bitmask(v),
        ),
        map(
            tuple((
                tag("thermal"),
                delimited(tag("("), map_res(digit1, str::parse::<f64>), tag(")")),
            )),
            |v| Check::Thermal(v),
        ),
        map(
            tuple((
                tag("sparsity"),
                delimited(tag("("), map_res(digit1, str::parse::<u32>), tag(")")),
            )),
            |v| Check::Sparsity(v),
        ),
    ))(input)
}

fn parse_constraint(input: &str) -> IResult<&str, Constraint> {
    map(
        tuple((
            tag("constraint"),
            delimited(multispace1, alpha1, multispace0),
            delimited(tag("@"), parse_priority, tag("{")),
            many0!(preceded!(multispace0, parse_check)),
            tag("}"),
        )),
        |(_, name, priority, checks, _)| Constraint { name: String::from(name), priority, checks },
    )(input)
}

fn parse_constraint_group(input: &str) -> IResult<&str, ConstraintGroup> {
    map(
        tuple((
            tag("constraint_group"),
            delimited(multispace1, alpha1, multispace0),
            delimited(tag("@"), map_res(tag("require_all"), |_| Ok(true)), tag("{")),
            separated_list0!(tuple!(multispace0, tag("//"), multispace0, take_while1!(|c| c != '\n')), alpha1),
            tag("}"),
        )),
        |(_, name, require_all, constraints, _)| ConstraintGroup { name: String::from(name), require_all, constraints },
    )(input)
}

fn parse_override(input: &str) -> IResult<&str, OverrideDecl> {
    map(
        tuple((
            tag("@override"),
            delimited(tag("("), alpha1, tag(",")),
            alpha1,
            tag(")"),
        )),
        |(_, constraint, over, _)| OverrideDecl { constraint: String::from(constraint), over: String::from(over) },
    )(input)
}

fn parse_weaken(input: &str) -> IResult<&str, WeakenDecl> {
    map(
        tuple((
            tag("@weaken"),
            delimited(tag("("), tuple((map_res(digit1, str::parse::<f64>), tag("->"), map_res(digit1, str::parse::<f64>))), tag(")")),
        )),
        |(_, (start, _, end), _)| WeakenDecl { range: (start, end) },
    )(input)
}

pub fn parse_guard(input: &str) -> IResult<&str, Vec<GuardItem>> {
    let comment = tuple!(tag("//"), take_while1!(|c| c != '\n'));
    let ws = delimited(multispace0, alt!((parse_constraint, parse_constraint_group, parse_override, parse_weaken)), multispace0);
    fold_many0!(ws, Vec::new(), |mut acc, item| { acc.push(item); acc })(input)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_constraint() {
        let input = r#"constraint eVTOL_altitude @priority(HARD) {
            range(activation[0], 0, 15000)
            whitelist(activation[1], {HOVER, ASCEND, DESCEND, LAND, EMERGENCY})
            bitmask(activation[2], 0x3F)
            thermal(2.5)
            sparsity(128)
        }"#;
        let expected = Constraint {
            name: String::from("eVTOL_altitude"),
            priority: Priority::Hard,
            checks: vec![
                Check::Range { start: 0.0, end: 15000.0 },
                Check::Whitelist(vec![String::from("HOVER"), String::from("ASCEND"), String::from("DESCEND"), String::from("LAND"), String::from("EMERGENCY")]),
                Check::Bitmask(0x3F),
                Check::Thermal(2.5),
                Check::Sparsity(128),
            ],
        };
        assert_eq!(parse_constraint(input).unwrap().1, expected);
    }

    #[test]
    fn test_parse_constraint_group() {
        let input = r#"constraint_group flight_safety @require_all {
            // constraints here
            eVTOL_altitude
            eVTOL_speed
        }"#;
        let expected = ConstraintGroup {
            name: String::from("flight_safety"),
            require_all: true,
            constraints: vec![String::from("eVTOL_altitude"), String::from("eVTOL_speed")],
        };
        assert_eq!(parse_constraint_group(input).unwrap().1, expected);
    }

    #[test]
    fn test_parse_override() {
        let input = r#"@override(eVTOL_altitude over emergency_landing)"#;
        let expected = OverrideDecl {
            constraint: String::from("eVTOL_altitude"),
            over: String::from("emergency_landing"),
        };
        assert_eq!(parse_override(input).unwrap().1, expected);
    }

    #[test]
    fn test_parse_weaken() {
        let input = r#"@weaken(range: [0, 15000] -> [0, 50000])"#;
        let expected = WeakenDecl { range: (0.0, 50000.0) };
        assert_eq!(parse_weaken(input).unwrap().1, expected);
    }

    #[test]
    fn test_parse_guard() {
        let input = r#"constraint eVTOL_altitude @priority(HARD) {
            range(activation[0], 0, 15000)
            whitelist(activation[1], {HOVER, ASCEND, DESCEND, LAND, EMERGENCY})
            bitmask(activation[2], 0x3F)
            thermal(2.5)
            sparsity(128)
        }
        constraint_group flight_safety @require_all {
            // constraints here
            eVTOL_altitude
            eVTOL_speed
        }
        @override(eVTOL_altitude over emergency_landing)
        @weaken(range: [0, 15000] -> [0, 50000])"#;
        let expected = vec![
            GuardItem::Constraint(Constraint {
                name: String::from("eVTOL_altitude"),
                priority: Priority::Hard,
                checks: vec![
                    Check::Range { start: 0.0, end: 15000.0 },
                    Check::Whitelist(vec![String::from("HOVER"), String::from("ASCEND"), String::from("DESCEND"), String::from("LAND"), String::from("EMERGENCY")]),
                    Check::Bitmask(0x3F),
                    Check::Thermal(2.5),
                    Check::Sparsity(128),
                ],
            }),
            GuardItem::ConstraintGroup(ConstraintGroup {
                name: String::from("flight_safety"),
                require_all: true,
                constraints: vec![String::from("eVTOL_altitude"), String::from("eVTOL_speed")],
            }),
            GuardItem::Override(OverrideDecl {
                constraint: String::from("eVTOL_altitude"),
                over: String::from("emergency_landing"),
            }),
            GuardItem::Weaken(WeakenDecl { range: (0.0, 50000.0) }),
        ];
        assert_eq!(parse_guard(input).unwrap().1, expected);
    }
}
