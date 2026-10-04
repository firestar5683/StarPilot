#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8327048500586505475);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1345819323802691490);
void pose_H_mod_fun(double *state, double *out_8287360551876046332);
void pose_f_fun(double *state, double dt, double *out_76477989752059892);
void pose_F_fun(double *state, double dt, double *out_2587667055193245078);
void pose_h_4(double *state, double *unused, double *out_8356936087827293267);
void pose_H_4(double *state, double *unused, double *out_117195959047770632);
void pose_h_10(double *state, double *unused, double *out_4187746716742178647);
void pose_H_10(double *state, double *unused, double *out_4255482199594732963);
void pose_h_13(double *state, double *unused, double *out_631883575165978985);
void pose_H_13(double *state, double *unused, double *out_3095077866284562169);
void pose_h_14(double *state, double *unused, double *out_6652898583954639418);
void pose_H_14(double *state, double *unused, double *out_552312485692654231);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}