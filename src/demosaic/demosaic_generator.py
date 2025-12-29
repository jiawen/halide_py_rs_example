import halide as hl

x, y, c, xi, yi, yo, yii = hl.vars("x y c xi yi yo yii")


def red_xy_offset(cfa_pattern: hl.Expr) -> (hl.Expr, hl.Expr):
    # Returns the (x, y) offset of the red pixel in the 2x2 CFA pattern, as
    # Int32.
    x_offset = hl.cast(hl.Int(32), cfa_pattern % 2)
    y_offset = hl.cast(hl.Int(32), cfa_pattern / 2)
    return x_offset, y_offset


def deinterleave(bayer: hl.Func, cfa_pattern: hl.Expr) -> hl.Func:
    # Deinterleaves a single-channel Bayer image to 4-channel Func where:
    # - the channels are orderd R, Gr, Gb, B
    # - pixel (x = 0, y = 0) is always red.
    #   - Depending on `cfa_pattern`, the output may be shifted so that min
    #   in either x or y may be -1.
    #   - the output extents are always half that of the input in both
    #   dimensions.
    deinterleaved = hl.Func("deinterleaved")

    # The red index in row-major order corresponds to the CFA pattern enum.
    # 0: R G    x_offset = 0
    #    G B    y_offset = 0
    # 1: G R    x_offset = 1
    #    B G    y_offset = 0
    # 2: G B    x_offset = 0
    #    R G    y_offset = 1
    # 3: B G    x_offset = 1
    #    G R    y_offset = 1
    x_offset, y_offset = red_xy_offset(cfa_pattern)

    # Shift `bayer` such that red is at (0, 0).
    shifted = hl.Func("shifted")
    shifted[x, y] = bayer[x + x_offset, y + y_offset]

    # Now that red is at (0, 0), we can mux over c to always get (R, Gr, Gb, B).
    deinterleaved[x, y, c] = hl.mux(c, [
        shifted[2 * x, 2 * y], shifted[2 * x + 1, 2 * y],
        shifted[2 * x, 2 * y + 1], shifted[2 * x + 1, 2 * y + 1]
    ])

    return deinterleaved


# Average two positive values rounding up
# TODO: Expr(a) is gross. Because we often pass in a FuncRef, which doesn't
# .type(). Halide says they might just add FuncRef::type() (and a binding).
def avg(a, b) -> hl.Expr:
    a = hl.Expr(a)
    wider = a.type().with_bits(a.type().bits() * 2)
    return hl.cast(a.type(), (hl.cast(wider, a) + b + 1) / 2)


def interleave_x(a: hl.Func, b: hl.Func) -> hl.Func:
    out = hl.Func()
    out[x, y] = hl.select((x % 2) == 0, a[x / 2, y], b[x / 2, y])
    return out


def interleave_y(a: hl.Func, b: hl.Func) -> hl.Func:
    out = hl.Func()
    out[x, y] = hl.select((y % 2) == 0, a[x, y / 2], b[x, y / 2])
    return out


@hl.generator(name="demosaic_generator")
class DemosaicGenerator:
    # input: a single-channel bayer pattern image.
    input = hl.InputBuffer(hl.UInt(16), 2)

    # 0: RGGB, 1: GRBG, 2: GBRG, 3: BGGR
    # These enum values match that of Android Camera2.
    # More conveniently, they correspond to the index of the red pixel (when
    # the 2x2 pattern is flattened row-major).
    cfa_pattern = hl.InputScalar(hl.UInt(8))

    # TODO: add optional active area / default crop / default user crop (in DNG parlance)

    # Note that the output is a signed integer as interpolation may produce
    # negative values.
    output = hl.OutputBuffer(hl.Int(16), 3)

    def generate(self):
        # Clamp input such that every *two* rows and columns are repeated.
        input_clamped = hl.Func("input_clamped")
        x_clamped = hl.clamp(x, x % 2, self.input.width() - 2 + x % 2)
        y_clamped = hl.clamp(y, y % 2, self.input.height() - 2 + y % 2)
        input_clamped[x, y] = self.input[x_clamped, y_clamped]

        # Deinterleave to r, gr, gb, b (aka RGGB).
        deinterleaved = deinterleave(input_clamped, self.cfa_pattern)

        # TODO: all math is done in int32. int16 might be much faster.
        casted = hl.Func("casted")
        casted[x, y, c] = hl.cast(hl.Int(32), deinterleaved[x, y, c])

        # Use the notation {x}_{y} for the value of channel x at a site in the
        # input of channel y.

        # Give more convenient names to the four channels we know.
        r_r, g_gr, g_gb, b_b = hl.funcs("r_r g_gr g_gb b_b")
        r_r[x, y] = casted[x, y, 0]
        g_gr[x, y] = casted[x, y, 1]
        g_gb[x, y] = casted[x, y, 2]
        b_b[x, y] = casted[x, y, 3]

        # These are the values we need to interpolate.
        b_r, g_r, b_gr, r_gr, b_gb, r_gb, r_b, g_b = hl.funcs(
            "b_r, g_r, b_gr, r_gr, b_gb, r_gb, r_b, g_b")

        # First calculate green at the red and blue sites.

        # Try interpolating vertically and horizontally. Also compute differences
        # vertically and horizontally. Use interpolation in whichever direction had
        # the smallest difference.
        gv_r = avg(g_gb[x, y - 1], g_gb[x, y])
        gvd_r = hl.absd(g_gb[x, y - 1], g_gb[x, y])
        gh_r = avg(g_gr[x - 1, y], g_gr[x, y])
        ghd_r = hl.absd(g_gr[x - 1, y], g_gr[x, y])

        g_r[x, y] = hl.select(ghd_r < gvd_r, gh_r, gv_r)

        # For green at blue locations (it's like switching B and R compared to
        # green at red!). So all signs switch compared to green at red.
        gv_b = avg(g_gr[x, y + 1], g_gr[x, y])
        gvd_b = hl.absd(g_gr[x, y + 1], g_gr[x, y])
        gh_b = avg(g_gb[x + 1, y], g_gb[x, y])
        ghd_b = hl.absd(g_gb[x + 1, y], g_gb[x, y])

        g_b[x, y] = hl.select(ghd_b < gvd_b, gh_b, gv_b)

        # Next, interpolate red at gr by first interpolating, then correcting using
        # the error green would have had if we had interpolated it in the same way
        # (i.e., add the second derivative of the green channel at the same place).
        correction = hl.Expr()

        correction = g_gr[x, y] - avg(g_r[x, y], g_r[x + 1, y])
        r_gr[x, y] = correction + avg(r_r[x, y], r_r[x + 1, y])

        # Do the same for other reds and blues at green sites
        correction = g_gr[x, y] - avg(g_b[x, y], g_b[x, y - 1])
        b_gr[x, y] = correction + avg(b_b[x, y], b_b[x, y - 1])

        correction = g_gb[x, y] - avg(g_r[x, y], g_r[x, y + 1])
        r_gb[x, y] = correction + avg(r_r[x, y], r_r[x, y + 1])

        correction = g_gb[x, y] - avg(g_b[x, y], g_b[x - 1, y])
        b_gb[x, y] = correction + avg(b_b[x, y], b_b[x - 1, y])

        # Now interpolate diagonally to get red at blue and blue at red. Hold onto
        # your hats this gets really fancy. We do the same thing as for
        # interpolating green where we try both directions (in this case the
        # positive and negative diagonals), and use the one with the lowest
        # absolute difference. But we also use the same trick as interpolating red
        # and blue at green sites - we correct our interpolations using the second
        # derivative of green at the same sites.

        correction = g_b[x, y] - avg(g_r[x, y], g_r[x + 1, y + 1])
        rp_b = correction + avg(r_r[x, y], r_r[x + 1, y + 1])
        rpd_b = hl.absd(r_r[x, y], r_r[x + 1, y + 1])

        correction = g_b[x, y] - avg(g_r[x + 1, y], g_r[x, y + 1])
        rn_b = correction + avg(r_r[x + 1, y], r_r[x, y + 1])
        rnd_b = hl.absd(r_r[x + 1, y], r_r[x, y + 1])

        r_b[x, y] = hl.select(rpd_b < rnd_b, rp_b, rn_b)

        # Same thing for blue at red.
        correction = g_r[x, y] - avg(g_b[x, y], g_b[x - 1, y - 1])
        bp_r = correction + avg(b_b[x, y], b_b[x - 1, y - 1])
        bpd_r = hl.absd(b_b[x, y], b_b[x - 1, y - 1])

        correction = g_r[x, y] - avg(g_b[x - 1, y], g_b[x, y - 1])
        bn_r = correction + avg(b_b[x - 1, y], b_b[x, y - 1])
        bnd_r = hl.absd(b_b[x - 1, y], b_b[x, y - 1])

        b_r[x, y] = hl.select(bpd_r < bnd_r, bp_r, bn_r)

        # Generate the full-resolution color channels by interleaving.
        r, g, b = hl.funcs("r g b")
        r = interleave_y(interleave_x(r_r, r_gr), interleave_x(r_gb, r_b))
        g = interleave_y(interleave_x(g_r, g_gr), interleave_x(g_gb, g_b))
        b = interleave_y(interleave_x(b_r, b_gr), interleave_x(b_gb, b_b))

        # Mux them together to make the 3-channel output.
        rgb = hl.Func("rgb")
        rgb[x, y, c] = hl.mux(c, [r[x, y], g[x, y], b[x, y]])

        x_offset, y_offset = red_xy_offset(self.cfa_pattern)

        # TODO: if we support a crop rectangle, then it's
        # `rgb[x - x_offset + crop[0], y - y_offset + crop[1]]`.
        self.output[x, y, c] = hl.cast(hl.Int(16), rgb[x - x_offset,
                                                       y - y_offset, c])

        ##### Schedule #####
        if self.target().has_gpu_feature():
            xi, yi = hl.vars("xi yi")
            self.output.gpu_tile(x, y, xi, yi, 16, 16)
        else:
            vec = self.natural_vector_size(hl.UInt(16))

            xi, yi = hl.vars("xi yi")
            (self.output.tile(x, y, xi, yi, 128,
                              16).vectorize(xi, vec).reorder(c, x,
                                                             y).parallel(y))

            (r.store_at(self.output, x).compute_at(self.output,
                                                   xi).vectorize(x, vec))
            (g.store_at(self.output, x).compute_at(self.output,
                                                   xi).vectorize(x, vec))
            (b.store_at(self.output, x).compute_at(self.output,
                                                   xi).vectorize(x, vec))


if __name__ == "__main__":
    hl.main()
