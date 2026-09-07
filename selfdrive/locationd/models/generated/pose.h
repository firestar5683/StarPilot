#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5867685499485526905);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7496427572072330735);
void pose_H_mod_fun(double *state, double *out_4599731282943687674);
void pose_f_fun(double *state, double dt, double *out_8448766243959956852);
void pose_F_fun(double *state, double dt, double *out_3524034210859456461);
void pose_h_4(double *state, double *unused, double *out_1468084297579901706);
void pose_H_4(double *state, double *unused, double *out_552787102095393061);
void pose_h_10(double *state, double *unused, double *out_1051779536617211070);
void pose_H_10(double *state, double *unused, double *out_7440841037325716699);
void pose_h_13(double *state, double *unused, double *out_4266757043601180240);
void pose_H_13(double *state, double *unused, double *out_3765060927427725862);
void pose_h_14(double *state, double *unused, double *out_1847032621455587499);
void pose_H_14(double *state, double *unused, double *out_117670575450509462);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}