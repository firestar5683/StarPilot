#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5436717349763929250);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2267989734965085487);
void pose_H_mod_fun(double *state, double *out_7252406541217060893);
void pose_f_fun(double *state, double dt, double *out_7195877540201438501);
void pose_F_fun(double *state, double dt, double *out_2191763838467757291);
void pose_h_4(double *state, double *unused, double *out_6710764914604440332);
void pose_H_4(double *state, double *unused, double *out_9072105267123357754);
void pose_h_10(double *state, double *unused, double *out_5397643117837077736);
void pose_H_10(double *state, double *unused, double *out_8486068256269040489);
void pose_h_13(double *state, double *unused, double *out_1020156160635096483);
void pose_H_13(double *state, double *unused, double *out_5859831441791024953);
void pose_h_14(double *state, double *unused, double *out_6027370464870412024);
void pose_H_14(double *state, double *unused, double *out_5108864410783873225);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}