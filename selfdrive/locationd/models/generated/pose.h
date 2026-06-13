#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3341780452292505997);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5409150910353518766);
void pose_H_mod_fun(double *state, double *out_8300172317114018464);
void pose_f_fun(double *state, double dt, double *out_4063489601932878054);
void pose_F_fun(double *state, double dt, double *out_493800117352810078);
void pose_h_4(double *state, double *unused, double *out_6026765849154187968);
void pose_H_4(double *state, double *unused, double *out_7102224835231120360);
void pose_h_10(double *state, double *unused, double *out_1866086890220189324);
void pose_H_10(double *state, double *unused, double *out_834802170779042492);
void pose_h_13(double *state, double *unused, double *out_4520826989648677276);
void pose_H_13(double *state, double *unused, double *out_3889951009898787559);
void pose_h_14(double *state, double *unused, double *out_733646167343188736);
void pose_H_14(double *state, double *unused, double *out_8261730806183058960);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}