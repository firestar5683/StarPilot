#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7675941765646048454);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6578985106349638079);
void pose_H_mod_fun(double *state, double *out_8249219982215908455);
void pose_f_fun(double *state, double dt, double *out_741196485394149917);
void pose_F_fun(double *state, double dt, double *out_914245573923806659);
void pose_h_4(double *state, double *unused, double *out_1661592600804563205);
void pose_H_4(double *state, double *unused, double *out_3634592945286592091);
void pose_h_10(double *state, double *unused, double *out_1540829144479980375);
void pose_H_10(double *state, double *unused, double *out_3859318150895892325);
void pose_h_13(double *state, double *unused, double *out_1494548337638663963);
void pose_H_13(double *state, double *unused, double *out_422319119954259290);
void pose_h_14(double *state, double *unused, double *out_4998597365434596125);
void pose_H_14(double *state, double *unused, double *out_328647911052892438);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}