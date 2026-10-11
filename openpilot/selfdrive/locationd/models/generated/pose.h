#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3762875391382386195);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1907257459040696591);
void pose_H_mod_fun(double *state, double *out_4096443015319918083);
void pose_f_fun(double *state, double dt, double *out_6359004595403005878);
void pose_F_fun(double *state, double dt, double *out_6678289125726224618);
void pose_h_4(double *state, double *unused, double *out_8702070268431109774);
void pose_H_4(double *state, double *unused, double *out_1056075369719162652);
void pose_h_10(double *state, double *unused, double *out_4563905700114918382);
void pose_H_10(double *state, double *unused, double *out_7730657328515761584);
void pose_h_13(double *state, double *unused, double *out_8383994934843595415);
void pose_H_13(double *state, double *unused, double *out_2777680093583361372);
void pose_h_14(double *state, double *unused, double *out_8323654106391695519);
void pose_H_14(double *state, double *unused, double *out_2026713062576209644);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}