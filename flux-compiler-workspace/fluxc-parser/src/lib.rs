use fluxc_ast::{Expr, Ident};
use thiserror::Error;

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum ParseError {
    #[error("unexpected end of input")]
    Eof,
    #[error("unexpected token: expected {expected}, found {found}")]
    UnexpectedToken { expected: String, found: String },
    #[error("invalid number: {0}")]
    InvalidNumber(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum Token {
    Ident(String),
    Number(u64),
    Hex(u64),
    In,
    Domain,
    LBracket,
    RBracket,
    LParen,
    RParen,
    Comma,
    EqEq,
    And,
    Or,
    Not,
    Eof,
}

struct Lexer<'a> {
    input: &'a str,
    pos: usize,
}

impl<'a> Lexer<'a> {
    fn new(input: &'a str) -> Self {
        Self { input, pos: 0 }
    }

    fn peek_char(&self) -> Option<char> {
        self.input.get(self.pos..)?.chars().next()
    }

    fn advance(&mut self) -> Option<char> {
        let ch = self.peek_char()?;
        self.pos += ch.len_utf8();
        Some(ch)
    }

    fn skip_whitespace(&mut self) {
        while let Some(ch) = self.peek_char() {
            if ch.is_whitespace() {
                let _ = self.advance();
            } else {
                break;
            }
        }
    }

    fn next_token(&mut self) -> Result<Token, ParseError> {
        self.skip_whitespace();
        if self.pos >= self.input.len() {
            return Ok(Token::Eof);
        }

        let ch = match self.peek_char() {
            Some(c) => c,
            None => return Ok(Token::Eof),
        };

        match ch {
            '[' => {
                self.advance();
                Ok(Token::LBracket)
            }
            ']' => {
                self.advance();
                Ok(Token::RBracket)
            }
            '(' => {
                self.advance();
                Ok(Token::LParen)
            }
            ')' => {
                self.advance();
                Ok(Token::RParen)
            }
            ',' => {
                self.advance();
                Ok(Token::Comma)
            }
            '=' => {
                self.advance();
                if self.peek_char() == Some('=') {
                    self.advance();
                    Ok(Token::EqEq)
                } else {
                    Err(ParseError::UnexpectedToken {
                        expected: "==".to_string(),
                        found: "=".to_string(),
                    })
                }
            }
            '0'
                if match self.input.get(self.pos..) {
                    Some(rest) => rest.starts_with("0x") || rest.starts_with("0X"),
                    None => false,
                } =>
            {
                self.advance();
                self.advance();
                let start = self.pos;
                while let Some(c) = self.peek_char() {
                    if c.is_ascii_hexdigit() {
                        let _ = self.advance();
                    } else {
                        break;
                    }
                }
                let hex_str = &self.input[start..self.pos];
                let val = u64::from_str_radix(hex_str, 16)
                    .map_err(|_| ParseError::InvalidNumber(hex_str.to_string()))?;
                Ok(Token::Hex(val))
            }
            c if c.is_ascii_digit() => {
                let start = self.pos;
                while let Some(c) = self.peek_char() {
                    if c.is_ascii_digit() {
                        let _ = self.advance();
                    } else {
                        break;
                    }
                }
                let num_str = &self.input[start..self.pos];
                let val = num_str
                    .parse::<u64>()
                    .map_err(|_| ParseError::InvalidNumber(num_str.to_string()))?;
                Ok(Token::Number(val))
            }
            c if c.is_alphabetic() || c == '_' => {
                let start = self.pos;
                while let Some(c) = self.peek_char() {
                    if c.is_alphanumeric() || c == '_' {
                        let _ = self.advance();
                    } else {
                        break;
                    }
                }
                let ident = &self.input[start..self.pos];
                match ident.to_ascii_uppercase().as_str() {
                    "IN" => Ok(Token::In),
                    "DOMAIN" => Ok(Token::Domain),
                    "AND" => Ok(Token::And),
                    "OR" => Ok(Token::Or),
                    "NOT" => Ok(Token::Not),
                    _ => Ok(Token::Ident(ident.to_string())),
                }
            }
            _ => {
                let s = ch.to_string();
                self.advance();
                Err(ParseError::UnexpectedToken {
                    expected: "valid token".to_string(),
                    found: s,
                })
            }
        }
    }
}

struct Parser<'a> {
    lexer: Lexer<'a>,
    current: Token,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Result<Self, ParseError> {
        let mut lexer = Lexer::new(input);
        let current = lexer.next_token()?;
        Ok(Self { lexer, current })
    }

    fn advance(&mut self) -> Result<(), ParseError> {
        self.current = self.lexer.next_token()?;
        Ok(())
    }

    fn expect(&mut self, token: Token) -> Result<(), ParseError> {
        let matches = match (&self.current, &token) {
            (Token::Ident(_), Token::Ident(_)) => true,
            (Token::Number(_), Token::Number(_)) => true,
            (Token::Hex(_), Token::Hex(_)) => true,
            (a, b) => a == b,
        };
        if matches {
            self.advance()
        } else {
            Err(ParseError::UnexpectedToken {
                expected: format!("{:?}", token),
                found: format!("{:?}", self.current),
            })
        }
    }

    fn parse_expr(&mut self) -> Result<Expr, ParseError> {
        self.parse_or()
    }

    fn parse_or(&mut self) -> Result<Expr, ParseError> {
        let mut lhs = self.parse_and()?;
        while self.current == Token::Or {
            self.advance()?;
            let rhs = self.parse_and()?;
            lhs = Expr::or(lhs, rhs);
        }
        Ok(lhs)
    }

    fn parse_and(&mut self) -> Result<Expr, ParseError> {
        let mut lhs = self.parse_not()?;
        while self.current == Token::And {
            self.advance()?;
            let rhs = self.parse_not()?;
            lhs = Expr::and(lhs, rhs);
        }
        Ok(lhs)
    }

    fn parse_not(&mut self) -> Result<Expr, ParseError> {
        if self.current == Token::Not {
            self.advance()?;
            let inner = self.parse_not()?;
            Ok(Expr::not(inner))
        } else {
            self.parse_primary()
        }
    }

    fn parse_primary(&mut self) -> Result<Expr, ParseError> {
        match &self.current {
            Token::Ident(name) => {
                let name = Ident(name.clone());
                self.advance()?;
                match &self.current {
                    Token::In => {
                        self.advance()?;
                        if self.current == Token::Domain {
                            self.advance()?;
                            match self.current {
                                Token::Hex(mask) => {
                                    let mask = mask;
                                    self.advance()?;
                                    Ok(Expr::Domain { name, mask })
                                }
                                Token::Number(mask) => {
                                    let mask = mask;
                                    self.advance()?;
                                    Ok(Expr::Domain { name, mask })
                                }
                                _ => Err(ParseError::UnexpectedToken {
                                    expected: "hex or number mask".to_string(),
                                    found: format!("{:?}", self.current),
                                }),
                            }
                        } else if self.current == Token::LBracket {
                            self.advance()?;
                            let lo = match self.current {
                                Token::Number(n) => {
                                    let n = n;
                                    self.advance()?;
                                    n
                                }
                                _ => {
                                    return Err(ParseError::UnexpectedToken {
                                        expected: "number".to_string(),
                                        found: format!("{:?}", self.current),
                                    })
                                }
                            };
                            self.expect(Token::Comma)?;
                            let hi = match self.current {
                                Token::Number(n) => {
                                    let n = n;
                                    self.advance()?;
                                    n
                                }
                                _ => {
                                    return Err(ParseError::UnexpectedToken {
                                        expected: "number".to_string(),
                                        found: format!("{:?}", self.current),
                                    })
                                }
                            };
                            self.expect(Token::RBracket)?;
                            Ok(Expr::Range { name, lo, hi })
                        } else {
                            Err(ParseError::UnexpectedToken {
                                expected: "domain or [".to_string(),
                                found: format!("{:?}", self.current),
                            })
                        }
                    }
                    Token::EqEq => {
                        self.advance()?;
                        let val = match self.current {
                            Token::Number(n) => {
                                let n = n;
                                self.advance()?;
                                n
                            }
                            _ => {
                                return Err(ParseError::UnexpectedToken {
                                    expected: "number".to_string(),
                                    found: format!("{:?}", self.current),
                                })
                            }
                        };
                        Ok(Expr::Exact { name, val })
                    }
                    _ => Err(ParseError::UnexpectedToken {
                        expected: "in or ==".to_string(),
                        found: format!("{:?}", self.current),
                    }),
                }
            }
            Token::LParen => {
                self.advance()?;
                let expr = self.parse_expr()?;
                self.expect(Token::RParen)?;
                Ok(expr)
            }
            _ => Err(ParseError::UnexpectedToken {
                expected: "identifier or (".to_string(),
                found: format!("{:?}", self.current),
            }),
        }
    }
}

pub fn parse(input: &str) -> Result<Expr, ParseError> {
    let mut parser = Parser::new(input)?;
    let expr = parser.parse_expr()?;
    if parser.current != Token::Eof {
        return Err(ParseError::UnexpectedToken {
            expected: "EOF".to_string(),
            found: format!("{:?}", parser.current),
        });
    }
    Ok(expr)
}
