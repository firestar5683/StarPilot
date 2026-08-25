#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_4409321269442810496);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3789556254182165506);
void pose_H_mod_fun(double *state, double *out_3068405914716205428);
void pose_f_fun(double *state, double dt, double *out_5515990809264108996);
void pose_F_fun(double *state, double dt, double *out_1412435369220653896);
void pose_h_4(double *state, double *unused, double *out_7211674724064901455);
void pose_H_4(double *state, double *unused, double *out_8220924299755286163);
void pose_h_10(double *state, double *unused, double *out_7091555343827122853);
void pose_H_10(double *state, double *unused, double *out_3357399461201359920);
void pose_h_13(double *state, double *unused, double *out_4463366606757688719);
void pose_H_13(double *state, double *unused, double *out_7013545948621932652);
void pose_h_14(double *state, double *unused, double *out_2594435200759890716);
void pose_H_14(double *state, double *unused, double *out_6262578917614780924);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}