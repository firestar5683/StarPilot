#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3784924644306313628);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_540309216742292633);
void pose_H_mod_fun(double *state, double *out_6508658752892015980);
void pose_f_fun(double *state, double dt, double *out_7991760748331142667);
void pose_F_fun(double *state, double dt, double *out_2236499869103053430);
void pose_h_4(double *state, double *unused, double *out_8843213748921434845);
void pose_H_4(double *state, double *unused, double *out_3234436674101066727);
void pose_h_10(double *state, double *unused, double *out_3208643256414619500);
void pose_H_10(double *state, double *unused, double *out_6406759991116077694);
void pose_h_13(double *state, double *unused, double *out_7275462902737089254);
void pose_H_13(double *state, double *unused, double *out_6446710499433399528);
void pose_h_14(double *state, double *unused, double *out_3384719431142301101);
void pose_H_14(double *state, double *unused, double *out_7197677530440551256);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}