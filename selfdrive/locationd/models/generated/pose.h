#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_731387772078245243);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4206130707332622452);
void pose_H_mod_fun(double *state, double *out_2916011499501574438);
void pose_f_fun(double *state, double dt, double *out_4420889553799640425);
void pose_F_fun(double *state, double dt, double *out_586752082486093199);
void pose_h_4(double *state, double *unused, double *out_1330626957984611772);
void pose_H_4(double *state, double *unused, double *out_8068529884540655173);
void pose_h_10(double *state, double *unused, double *out_5440536108172962293);
void pose_H_10(double *state, double *unused, double *out_3777395375513848052);
void pose_h_13(double *state, double *unused, double *out_7911476404081815631);
void pose_H_13(double *state, double *unused, double *out_7165940363836563642);
void pose_h_14(double *state, double *unused, double *out_5129805537420960347);
void pose_H_14(double *state, double *unused, double *out_4985741452245282877);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}