use crate::types::*;
use nom::{
    bytes::complete::{tag, take_until},
    character::complete::{digit1, multispace0, alpha1, float},
    combinator::{map, map_res, opt},
    sequence::{delimited, preceded, tuple},
    IResult,
};

// ------------------------------
// AST (Parsed GUARD Spec)
// ------------------------------
#[derive(Clone, Debug)]
pub struct GuardSpec {
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub constraints: Vec<Constraint>,
}

// ------------------------------
// Parser Helpers
// ------------------------------
fn identifier(input: &str) -> IResult<&str, String> {
    map(alpha1, |s: &str| s.to_string())(input)
}

fn u32_num(input: &str) -> IResult<&str, u32> {
    map_res(digit1, |s: &str| s.parse::<u32>())(input)
}

fn i32_num(input: &str) -> IResult<&str, i32> {
    map_res(
        tuple((opt(tag("-")), digit1)),
        |(sign, s): (Option<&str>, &str)| {
            let num = s.parse::<i32>()?;
            Ok(if sign.is_some() { -num } else { num })
        },
    )(input)
}

// ------------------------------
// Constraint Parsers
// ------------------------------
fn parse_scope(input: &str) -> IResult<&str, Scope> {
    preceded(
        tag("SCOPE="),
        nom::branch::alt((
            map(tag("GLOBAL"), |_| Scope::Global),
            map(tag("ALL_ROWS"), |_| Scope::AllRows),
            map(tag("ALL_COLUMNS"), |_| Scope::AllColumns),
            map(preceded(tag("ROW="), u32_num), Scope::Row),
            map(preceded(tag("COLUMN="), u32_num), Scope::Column),
        )),
    )(input)
}

fn parse_sparsity_constraint(input: &str) -> IResult<&str, Constraint> {
    map(
        tuple((
            preceded(tag("SPARSITY("), delimited(multispace0, float, multispace0)),
            preceded(tag(", MAX_NON_ZERO="), delimited(multispace0, float, multispace0)),
            preceded(tag(","), delimited(multispace0, parse_scope, multispace0)),
        )),
        |(_, max_ratio, scope)| Constraint::Sparsity {
            max_non_zero_ratio: max_ratio,
            scope,
        },
    )(input)
}

// ------------------------------
// Top-Level Parser
// ------------------------------
pub fn parse_guard_dsl(input: &str) -> Result<GuardSpec, Guard2MaskError> {
    let result = tuple((
        preceded(multispace0, tag("GUARD")),
        preceded(multispace0, identifier),
        preceded(multispace0, tag("{")),
        // Parse DIMENSIONS
        preceded(
            multispace0,
            tuple((
                tag("DIMENSIONS"),
                preceded(multispace0, u32_num),
                preceded(multispace0, u32_num),
                tag(";"),
            )),
        ),
        // Parse constraints (simplified for example)
        preceded(
            multispace0,
            many0(preceded(
                tuple((multispace0, tag("CONSTRAINT"), multispace0)),
                nom::branch::alt((parse_sparsity_constraint, /* add others */)),
            )),
        ),
        preceded(multispace0, tag("}")),
    ))(input);

    match result {
        Ok((_, (_, name, _, (_, w, h, _), constraints, _))) => Ok(GuardSpec {
            name,
            width: w,
            height: h,
            constraints,
        }),
        Err(e) => Err(Guard2MaskError::ParseError(e.to_string())),
    }
}

// Helper for nom's many0 (omitted for brevity, included in full code)
fn many0<I, O, E, F>(mut f: F) -> impl FnMut(I) -> IResult<I, Vec<O>, E>
where
    F: FnMut(I) -> IResult<I, O, E>,
    I: Clone + PartialEq,
{
    move |mut i: I| {
        let mut acc = Vec::new();
        loop {
            let len = i.clone();
            match f(i) {
                Ok((i2, o)) => {
                    acc.push(o);
                    i = i2;
                    if i2 == len {
                        return Ok((i, acc));
                    }
                }
                Err(_) => return Ok((i, acc)),
            }
        }
    }
}
