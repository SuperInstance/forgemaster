use fluxc_ir::Module;

pub trait Pass {
    fn run(&self, module: &mut Module) -> Result<(), String>;
}

pub struct IdentityPass;

impl Pass for IdentityPass {
    fn run(&self, _module: &mut Module) -> Result<(), String> {
        Ok(())
    }
}

pub fn optimize(module: &mut Module, passes: &[&dyn Pass]) -> Result<(), String> {
    for pass in passes {
        pass.run(module)?;
    }
    Ok(())
}
