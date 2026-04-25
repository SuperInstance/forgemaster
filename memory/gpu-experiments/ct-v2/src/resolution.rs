#[derive(Debug, Clone, PartialEq)]
pub struct ResolutionConfig {
    pub max_c: i64,
    pub step_size: i64,
}

impl ResolutionConfig {
    pub fn low() -> Self {
        Self {
            max_c: 100,
            step_size: 1,
        }
    }

    pub fn medium() -> Self {
        Self {
            max_c: 1000,
            step_size: 1,
        }
    }

    pub fn high() -> Self {
        Self {
            max_c: 10000,
            step_size: 1,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolution_presets() {
        let low = ResolutionConfig::low();
        assert_eq!(low.max_c, 100);
        assert_eq!(low.step_size, 1);

        let medium = ResolutionConfig::medium();
        assert_eq!(medium.max_c, 1000);
        assert_eq!(medium.step_size, 1);

        let high = ResolutionConfig::high();
        assert_eq!(high.max_c, 10000);
        assert_eq!(high.step_size, 1);
    }
}
