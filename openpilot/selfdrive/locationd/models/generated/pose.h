#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8909220829729456592);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8068156223905085053);
void pose_H_mod_fun(double *state, double *out_3205830260465553476);
void pose_f_fun(double *state, double dt, double *out_4238396293587501899);
void pose_F_fun(double *state, double dt, double *out_6003141237729326165);
void pose_h_4(double *state, double *unused, double *out_6516003908446642780);
void pose_H_4(double *state, double *unused, double *out_8358348645504634211);
void pose_h_10(double *state, double *unused, double *out_5069419514865957544);
void pose_H_10(double *state, double *unused, double *out_2285557584559061390);
void pose_h_13(double *state, double *unused, double *out_3114619426317878324);
void pose_H_13(double *state, double *unused, double *out_6876121602872584604);
void pose_h_14(double *state, double *unused, double *out_5969212145833405866);
void pose_H_14(double *state, double *unused, double *out_6125154571865432876);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}