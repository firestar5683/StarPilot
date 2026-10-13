#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6769094018143345471);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7105507959452432978);
void pose_H_mod_fun(double *state, double *out_6619985577834044559);
void pose_f_fun(double *state, double dt, double *out_8911446702564060395);
void pose_F_fun(double *state, double dt, double *out_8001086797165012903);
void pose_h_4(double *state, double *unused, double *out_700157376215369055);
void pose_H_4(double *state, double *unused, double *out_5040670747730128630);
void pose_h_10(double *state, double *unused, double *out_157308656343122283);
void pose_H_10(double *state, double *unused, double *out_6282647945703286816);
void pose_h_13(double *state, double *unused, double *out_8562780767398180943);
void pose_H_13(double *state, double *unused, double *out_5795442117662722057);
void pose_h_14(double *state, double *unused, double *out_8175075787359245864);
void pose_H_14(double *state, double *unused, double *out_1957882315434756334);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}