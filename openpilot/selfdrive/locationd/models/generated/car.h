#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_3709339290753435113);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2695906871061935165);
void car_H_mod_fun(double *state, double *out_7521025143252519554);
void car_f_fun(double *state, double dt, double *out_2870569988724221657);
void car_F_fun(double *state, double dt, double *out_1340125705655256792);
void car_h_25(double *state, double *unused, double *out_1820458384291824141);
void car_H_25(double *state, double *unused, double *out_2436349258228458819);
void car_h_24(double *state, double *unused, double *out_809263190072562720);
void car_H_24(double *state, double *unused, double *out_259134834621308846);
void car_h_30(double *state, double *unused, double *out_3222422842442281109);
void car_H_30(double *state, double *unused, double *out_81983700278789808);
void car_h_26(double *state, double *unused, double *out_7423549809566033340);
void car_H_26(double *state, double *unused, double *out_868176711532341782);
void car_h_27(double *state, double *unused, double *out_1217142499615346624);
void car_H_27(double *state, double *unused, double *out_2092779611521635103);
void car_h_29(double *state, double *unused, double *out_5602594215076499458);
void car_H_29(double *state, double *unused, double *out_592215044593181992);
void car_h_28(double *state, double *unused, double *out_6547692270471837786);
void car_H_28(double *state, double *unused, double *out_4490183972476348582);
void car_h_31(double *state, double *unused, double *out_7005392194916958430);
void car_H_31(double *state, double *unused, double *out_241968609298990306);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}