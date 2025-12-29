import halide as hl

@hl.generator(name="add_generator")
class AddGenerator(hl.Generator):
    input = hl.InputBuffer(hl.Int(32), 1)
    output = hl.OutputBuffer(hl.Int(32), 1)

    def generate(self):
        g = self
        x = hl.Var("x")

        g.output[x] = g.input[x] + 1
        g.input.dim(0).set_stride(hl.Expr())
        g.output.compute_root()


if __name__ == "__main__":
    hl.main()
