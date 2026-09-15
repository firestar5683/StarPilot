#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_9222670015265418032);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6734711869955682828);
void pose_H_mod_fun(double *state, double *out_3054834377026573453);
void pose_f_fun(double *state, double dt, double *out_6521868085604382140);
void pose_F_fun(double *state, double dt, double *out_7891921077140001268);
void pose_h_4(double *state, double *unused, double *out_6238203153530464174);
void pose_H_4(double *state, double *unused, double *out_8902916183778532174);
void pose_h_10(double *state, double *unused, double *out_479264188908505210);
void pose_H_10(double *state, double *unused, double *out_5035106138755480521);
void pose_h_13(double *state, double *unused, double *out_2296929327731223213);
void pose_H_13(double *state, double *unused, double *out_5690642358446199373);
void pose_h_14(double *state, double *unused, double *out_8770212541449767783);
void pose_H_14(double *state, double *unused, double *out_4939675327439047645);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}